#!/usr/bin/env bash
# Pose la situation du challenge k8s-challenge-contenir-une-attaque, fausse sur
# les sept états par construction :
#
#   - reservations : l'application légitime, trois réplicas derrière un Service ;
#   - l'accès de l'attaquant : le compte maintenance, un jeton longue durée
#     (Secret maintenance-jeton) et le ClusterRoleBinding maintenance vers le
#     ClusterRole edit, pour tout le cluster ;
#   - le Pod d'origine, diagnostic-reseau, sous ce compte ;
#   - la persistance : le DaemonSet collecteur-noeuds, déguisé en collecteur de
#     métriques et étiqueté comme une pièce de reservations, un Pod par nœud.
#     Toutes les 20 secondes, il recrée le compte, son jeton et sa liaison. Son
#     identité n'a que ces droits-là, et le verbe bind sur le seul edit ;
#   - calcul-lots : la charge abusive moulinette, deux réplicas sans requests ni
#     limits, sans quota ni LimitRange.
#
# LA CHARGE EST SÛRE POUR LE NŒUD PARTAGÉ : chaque Pod de moulinette écrit un
# bloc FIXE de 64 Mio dans un emptyDir en mémoire borné à 96 Mio, puis occupe
# un processeur 15 secondes sur 30. Moins de 150 Mio en tout, en BestEffort.
#
# L'UID du DaemonSet est relevé dans /var/lib/dsoxlab-labs : le constat doit le
# porter, preuve d'un export de l'objet vivant, donc avant sa suppression.
#
# Rejouable : tout ce qu'un passage précédent a laissé est retiré d'abord, le
# DaemonSet AVANT les liaisons, sans quoi il les recréerait aussitôt.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

REFERENCE=/var/lib/dsoxlab-labs/k8s-challenge-contenir-une-attaque.uid

# 1. Ce qu'un passage précédent aurait laissé.
if kubectl get namespace reservations >/dev/null 2>&1; then
  kubectl -n reservations delete daemonset collecteur-noeuds --ignore-not-found --cascade=foreground --wait=true --timeout=120s
fi
for ns in reservations calcul-lots; do
  kubectl delete namespace "$ns" --ignore-not-found --wait=true --timeout=180s
  if [[ "$(kubectl get namespace "$ns" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
    kubectl wait --for=delete "namespace/$ns" --timeout=180s
  fi
done
kubectl delete clusterrolebinding maintenance collecteur-noeuds --ignore-not-found
kubectl delete clusterrole collecteur-noeuds --ignore-not-found
# Toute autre liaison de cluster qui nommerait encore un compte de reservations.
kubectl get clusterrolebindings -o json \
  | python3 -c 'import json,sys; [print(b["metadata"]["name"]) for b in json.load(sys.stdin)["items"] if any(s.get("kind") == "ServiceAccount" and s.get("namespace") == "reservations" for s in b.get("subjects") or [])]' \
  | xargs -r kubectl delete clusterrolebinding
rm -f /root/constat-attaque.yaml "$REFERENCE"

# 2. La situation.
kubectl create namespace reservations
kubectl create namespace calcul-lots

cat <<'YAML' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: reservations
  namespace: reservations
  labels:
    app: reservations
    app.kubernetes.io/part-of: reservations
spec:
  replicas: 3
  selector:
    matchLabels:
      app: reservations
  template:
    metadata:
      labels:
        app: reservations
        app.kubernetes.io/part-of: reservations
    spec:
      automountServiceAccountToken: false
      containers:
        - name: web
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 50m
              memory: 32Mi
            limits:
              cpu: 200m
              memory: 128Mi
---
apiVersion: v1
kind: Service
metadata:
  name: reservations
  namespace: reservations
  labels:
    app.kubernetes.io/part-of: reservations
spec:
  selector:
    app: reservations
  ports:
    - port: 80
      targetPort: 80
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: maintenance
  namespace: reservations
---
apiVersion: v1
kind: Secret
metadata:
  name: maintenance-jeton
  namespace: reservations
  annotations:
    kubernetes.io/service-account.name: maintenance
type: kubernetes.io/service-account-token
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: maintenance
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: edit
subjects:
  - kind: ServiceAccount
    name: maintenance
    namespace: reservations
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: collecteur-noeuds
  namespace: reservations
  labels:
    app.kubernetes.io/part-of: reservations
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: collecteur-noeuds
rules:
  - apiGroups: [""]
    resources: ["serviceaccounts", "secrets"]
    verbs: ["create"]
  - apiGroups: ["rbac.authorization.k8s.io"]
    resources: ["clusterrolebindings"]
    verbs: ["create"]
  - apiGroups: ["rbac.authorization.k8s.io"]
    resources: ["clusterroles"]
    verbs: ["bind"]
    resourceNames: ["edit"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: collecteur-noeuds
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: collecteur-noeuds
subjects:
  - kind: ServiceAccount
    name: collecteur-noeuds
    namespace: reservations
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: collecteur-noeuds
  namespace: reservations
  labels:
    app: collecteur-noeuds
    app.kubernetes.io/part-of: reservations
spec:
  selector:
    matchLabels:
      app: collecteur-noeuds
  template:
    metadata:
      labels:
        app: collecteur-noeuds
        app.kubernetes.io/part-of: reservations
    spec:
      serviceAccountName: collecteur-noeuds
      tolerations:
        - operator: Exists
      containers:
        - name: metriques
          image: curlimages/curl:8.22.0@sha256:58adaa4e8dca9c988bae2aba4ab3434a0bb2da16bbe3f92dec39ec7785166777
          command:
            - sh
            - -c
            - |
              trap 'exit 0' TERM
              D=/var/run/secrets/kubernetes.io/serviceaccount
              API=https://kubernetes.default.svc
              appel() {
                curl -s -o /dev/null --cacert "$D/ca.crt" -H "Authorization: Bearer $(cat "$D/token")" \
                  -H "Content-Type: application/json" -X POST "$API$1" -d "$2"
              }
              while true; do
                appel /api/v1/namespaces/reservations/serviceaccounts \
                  '{"apiVersion":"v1","kind":"ServiceAccount","metadata":{"name":"maintenance","namespace":"reservations"}}'
                appel /api/v1/namespaces/reservations/secrets \
                  '{"apiVersion":"v1","kind":"Secret","type":"kubernetes.io/service-account-token","metadata":{"name":"maintenance-jeton","namespace":"reservations","annotations":{"kubernetes.io/service-account.name":"maintenance"}}}'
                appel /apis/rbac.authorization.k8s.io/v1/clusterrolebindings \
                  '{"apiVersion":"rbac.authorization.k8s.io/v1","kind":"ClusterRoleBinding","metadata":{"name":"maintenance"},"roleRef":{"apiGroup":"rbac.authorization.k8s.io","kind":"ClusterRole","name":"edit"},"subjects":[{"kind":"ServiceAccount","name":"maintenance","namespace":"reservations"}]}'
                sleep 20 &
                wait $!
              done
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              cpu: 100m
              memory: 64Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: diagnostic-reseau
  namespace: reservations
  labels:
    app: diagnostic-reseau
spec:
  serviceAccountName: maintenance
  containers:
    - name: diagnostic
      image: curlimages/curl:8.22.0@sha256:58adaa4e8dca9c988bae2aba4ab3434a0bb2da16bbe3f92dec39ec7785166777
      command: ["sh", "-c", "sleep infinity"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: moulinette
  namespace: calcul-lots
  labels:
    app: moulinette
spec:
  replicas: 2
  selector:
    matchLabels:
      app: moulinette
  template:
    metadata:
      labels:
        app: moulinette
    spec:
      automountServiceAccountToken: false
      containers:
        - name: calcul
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command:
            - sh
            - -c
            - |
              dd if=/dev/zero of=/travail/bloc bs=1M count=64
              while true; do
                timeout 15 sh -c 'while :; do :; done'
                sleep 15
              done
          volumeMounts:
            - name: travail
              mountPath: /travail
      volumes:
        - name: travail
          emptyDir:
            medium: Memory
            sizeLimit: 96Mi
YAML

kubectl -n reservations rollout status deployment/reservations --timeout=180s
kubectl -n reservations rollout status daemonset/collecteur-noeuds --timeout=180s
kubectl -n reservations wait --for=condition=Ready pod/diagnostic-reseau --timeout=180s
kubectl -n calcul-lots rollout status deployment/moulinette --timeout=180s

# 3. La référence du constat : l'UID du DaemonSet vivant, lisible par root seul.
mkdir -p "$(dirname "$REFERENCE")"
kubectl -n reservations get daemonset collecteur-noeuds -o jsonpath='{.metadata.uid}' > "$REFERENCE"
chmod 0600 "$REFERENCE"
test -s "$REFERENCE"

# La situation est posée quand l'accès de l'attaquant est réel.
test "$(kubectl auth can-i list secrets --all-namespaces --as system:serviceaccount:reservations:maintenance)" = yes
echo "Challenge posé : maintenance a edit sur tout le cluster, collecteur-noeuds le recrée, moulinette tourne sans plafond."
