#!/usr/bin/env bash
# Pose la situation de l'épreuve du niveau 3 sur le cluster kind « capacite »
# (un control plane, trois workers). Le setup a déjà réservé capacite-worker3
# (label et taint reserve=registre) et installé Traefik sur le NodePort 30080.
#
#   - metrics-server, pour que la mise à l'échelle ait des mesures à lire ;
#   - le namespace festival, hérité d'une équipe précédente :
#       billets    le frontend, deux exemplaires (busybox httpd), sans adresse ;
#       programme  l'application, un exemplaire, en root, sous le compte par
#                  défaut, sans requests, et sans adresse ;
#       un HPA sur programme (1 à 10) qui ne lit aucune métrique, faute de
#                  requests ;
#       registre   la base (postgres), qui vise le nœud réservé sans tolérer
#                  son taint : Pending ;
#       plafond    un ResourceQuota provisoire sur les requests, sans
#                  LimitRange ;
#       affiches   une charge sans ressources, créée après le plafond : son
#                  ReplicaSet ne crée aucun Pod (FailedCreate) ;
#   - le namespace paiement, avec le composant caisse EN PANNE : son Service
#     sélectionne version=v2, ses Pods portent version=v1, aucun endpoint ;
#   - le namespace partenaires, avec le Pod client partenaire ;
#   - ~/epreuve/, vide, où l'apprenant consigne la cause de la panne.
#
# Avant de rendre la main, le script mesure que la situation est bien celle-là,
# et que le cluster applique les NetworkPolicy : sans cela, deux critères
# seraient impossibles à réussir, et l'apprenant chercherait l'erreur chez lui.
# Rejouable : les namespaces sont recréés à chaque passage.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
RESERVE="capacite-worker3"
BUSYBOX="busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
POSTGRES="postgres:18.6-alpine@sha256:9ba53c7d41ea093baf5c1ba635ba5434c4f979880527d49bb7d9237d3193085b"
ECHO="hashicorp/http-echo:1.0.0@sha256:fcb75f691c8b0414d670ae570240cbf95502cc18a9ba57e982ecac589760a186"
MS_VERSION=v0.9.1
MS_IMAGE="registry.k8s.io/metrics-server/metrics-server:v0.9.1@sha256:9b0ba1926e1d3089673f45461c3c1416109dea33b3ba3434048defd380df329b"

# 1. Repartir de rien : les trois namespaces, et toute réservation d'un
#    passage précédent sur les autres nœuds.
# --ignore-not-found plutôt qu'un get préalable : un namespace encore en
# Terminating au moment du get disparaîtrait avant le delete (NotFound, set -e).
kubectl delete namespace festival paiement partenaires --ignore-not-found --wait=true --timeout=180s
for noeud in $(kubectl get nodes -o name); do
  [[ "$noeud" == "node/${RESERVE}" ]] && continue
  kubectl taint nodes "${noeud#node/}" reserve- 2>/dev/null || true
  kubectl label "$noeud" reserve- 2>/dev/null || true
done
kubectl label node "$RESERVE" reserve=registre --overwrite
kubectl taint node "$RESERVE" reserve=registre:NoSchedule --overwrite

# 2. metrics-server, avec --kubelet-insecure-tls (les kubelets de kind
#    présentent un certificat que metrics-server ne sait pas vérifier) et son
#    image épinglée par digest, comme le lab k8s-lire-l-etat-d-un-pod-en-erreur.
kubectl apply -f "https://github.com/kubernetes-sigs/metrics-server/releases/download/${MS_VERSION}/components.yaml"
if ! kubectl -n kube-system get deployment metrics-server -o jsonpath='{.spec.template.spec.containers[0].args}' \
    | grep -q -- '--kubelet-insecure-tls'; then
  kubectl -n kube-system patch deployment metrics-server --type=json -p '[
    {"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
fi
kubectl -n kube-system set image deployment/metrics-server metrics-server="${MS_IMAGE}"
kubectl -n kube-system rollout status deployment metrics-server --timeout=180s

# 3. Les namespaces.
kubectl create namespace festival
kubectl create namespace paiement
kubectl create namespace partenaires

# 4. festival : les deux applications web, la base, la mise à l'échelle.
#    Les pages viennent d'un ConfigMap, servies à la racine ET sous le chemin
#    de l'application : une route avec ou sans réécriture du chemin trouve la
#    page dans les deux cas.
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: billets-page
  namespace: festival
data:
  index.html: "billets"
  page: "billets"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: programme-page
  namespace: festival
data:
  index.html: "programme"
  page: "programme"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: billets
  namespace: festival
spec:
  replicas: 2
  selector:
    matchLabels:
      app: billets
  template:
    metadata:
      labels:
        app: billets
        role: frontend
    spec:
      containers:
        - name: billets
          image: ${BUSYBOX}
          command: ["httpd", "-f", "-p", "8080", "-h", "/www"]
          ports:
            - containerPort: 8080
          volumeMounts:
            - name: page
              mountPath: /www
      volumes:
        - name: page
          configMap:
            name: billets-page
            items:
              - key: index.html
                path: index.html
              - key: page
                path: billets/index.html
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: programme
  namespace: festival
spec:
  replicas: 1
  selector:
    matchLabels:
      app: programme
  template:
    metadata:
      labels:
        app: programme
    spec:
      containers:
        - name: programme
          image: ${BUSYBOX}
          command: ["httpd", "-f", "-p", "8080", "-h", "/www"]
          ports:
            - containerPort: 8080
          volumeMounts:
            - name: page
              mountPath: /www
      volumes:
        - name: page
          configMap:
            name: programme-page
            items:
              - key: index.html
                path: index.html
              - key: page
                path: programme/index.html
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: programme
  namespace: festival
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: programme
  minReplicas: 1
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
---
apiVersion: v1
kind: Service
metadata:
  name: registre
  namespace: festival
spec:
  selector:
    app: registre
  ports:
    - port: 5432
      targetPort: 5432
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: registre
  namespace: festival
spec:
  replicas: 1
  selector:
    matchLabels:
      app: registre
  template:
    metadata:
      labels:
        app: registre
    spec:
      nodeSelector:
        reserve: registre
      containers:
        - name: postgres
          image: ${POSTGRES}
          env:
            - name: POSTGRES_PASSWORD
              value: lab-seulement
          ports:
            - containerPort: 5432
EOF
kubectl -n festival rollout status deployment/billets deployment/programme --timeout=240s

# 5. Le plafond provisoire, posé APRÈS les applications : leurs Pods sans
#    requests existent déjà. La charge affiches, créée ensuite sans ressources,
#    est refusée par le plafond à chaque tentative de son ReplicaSet.
kubectl apply -f - <<EOF
apiVersion: v1
kind: ResourceQuota
metadata:
  name: plafond
  namespace: festival
spec:
  hard:
    requests.cpu: "1"
    requests.memory: 1Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: affiches
  namespace: festival
spec:
  replicas: 1
  selector:
    matchLabels:
      app: affiches
  template:
    metadata:
      labels:
        app: affiches
    spec:
      containers:
        - name: affiches
          image: ${BUSYBOX}
          command: ["sleep", "infinity"]
EOF

# 6. paiement : caisse, en panne de sélecteur.
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: caisse
  namespace: paiement
spec:
  replicas: 2
  selector:
    matchLabels:
      app: caisse
  template:
    metadata:
      labels:
        app: caisse
        version: v1
    spec:
      containers:
        - name: caisse
          image: ${ECHO}
          args: ["-text=caisse", "-listen=:5678"]
          ports:
            - containerPort: 5678
---
apiVersion: v1
kind: Service
metadata:
  name: caisse
  namespace: paiement
spec:
  selector:
    app: caisse
    version: v2
  ports:
    - port: 80
      targetPort: 5678
EOF

# 7. partenaires : le client d'un autre namespace.
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: partenaire
  namespace: partenaires
  labels:
    app: partenaire
spec:
  containers:
    - name: shell
      image: ${BUSYBOX}
      command: ["sleep", "infinity"]
EOF
kubectl -n paiement rollout status deployment/caisse --timeout=180s
kubectl -n partenaires wait --for=condition=Ready pod/partenaire --timeout=180s

# 8. Le répertoire où l'apprenant consigne la cause de la panne.
rm -rf "${LAB_HOME:?}/epreuve"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/epreuve"

# 9. La situation est-elle celle de l'énoncé ?
#    La base attend, faute de tolérer le taint du nœud réservé.
sleep 5
test "$(kubectl -n festival get pods -l app=registre -o jsonpath='{.items[*].status.phase}')" = "Pending"
#    affiches n'a aucun Pod : son ReplicaSet est refusé par le plafond.
for _ in $(seq 1 20); do
  if kubectl -n festival get rs -l app=affiches \
      -o jsonpath='{.items[*].status.conditions[*].type}' 2>/dev/null | grep -q ReplicaFailure; then
    break
  fi
  sleep 3
done
kubectl -n festival get rs -l app=affiches -o jsonpath='{.items[*].status.conditions[*].type}' | grep -q ReplicaFailure
test -z "$(kubectl -n festival get pods -l app=affiches -o name)"
#    caisse n'a aucun endpoint.
test -z "$(kubectl -n paiement get endpointslices -l kubernetes.io/service-name=caisse \
  -o jsonpath='{.items[*].endpoints[*].addresses[*]}')"

# 10. Le cluster applique-t-il les NetworkPolicy ? Un refus posé sur caisse doit
#     couper le partenaire, puis son retrait le rendre. Sans cette garantie, les
#     critères d'isolement de la base ne pourraient pas être réussis.
IP_CAISSE="$(kubectl -n paiement get pods -l app=caisse -o jsonpath='{.items[0].status.podIP}')"
kubectl -n partenaires exec partenaire -- nc -z -w 3 "$IP_CAISSE" 5678
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: controle-du-cni
  namespace: paiement
spec:
  podSelector:
    matchLabels:
      app: caisse
  policyTypes: ["Ingress"]
EOF
coupe=non
for _ in $(seq 1 20); do
  if ! kubectl -n partenaires exec partenaire -- nc -z -w 3 "$IP_CAISSE" 5678; then
    coupe=oui
    break
  fi
  sleep 3
done
kubectl -n paiement delete networkpolicy controle-du-cni
if [[ "$coupe" != "oui" ]]; then
  echo "Le CNI du cluster capacite n'applique pas les NetworkPolicy : l'épreuve ne peut pas se jouer." >&2
  exit 1
fi
for _ in $(seq 1 20); do
  kubectl -n partenaires exec partenaire -- nc -z -w 3 "$IP_CAISSE" 5678 && break
  sleep 3
done
kubectl -n partenaires exec partenaire -- nc -z -w 3 "$IP_CAISSE" 5678

# 11. Le point d'entrée HTTP répond sur le NodePort 30080 (404 : aucune route).
IP_NOEUD="$(kubectl get node capacite-control-plane -o jsonpath='{.status.addresses[?(@.type=="InternalIP")].address}')"
for _ in $(seq 1 20); do
  [[ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://${IP_NOEUD}:30080/")" == "404" ]] && break
  sleep 3
done
test "$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://${IP_NOEUD}:30080/")" = "404"

echo "Situation posée : registre en attente, affiches bloquée, caisse sans endpoint, rien n'est exposé."
