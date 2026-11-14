#!/usr/bin/env bash
# Pose la situation du challenge sur le cluster kind « capacite » (un control
# plane, trois workers) :
#
#   - metrics-server, pour que le HPA ait des mesures à lire ;
#   - aucun taint ni label du challenge sur les nœuds (dedie, disque) : c'est
#     à l'apprenant de les poser ;
#   - le namespace atelier, avec quatre applications posées SANS règle de
#     placement ni ressources :
#       rendu     l'application réservée (1 exemplaire) ;
#       accueil   l'application ordinaire, que le HPA mettra à l'échelle
#                 (2 exemplaires, busybox httpd) ;
#       stockage  l'application à placer par affinité de nœud (1 exemplaire) ;
#       galerie   l'application à répartir (2 exemplaires, busybox httpd) ;
#     aucun ResourceQuota, aucun LimitRange, aucun HPA.
#
# Rejouable : le namespace est recréé, les taints et labels d'un passage
# précédent sont retirés de tous les nœuds.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

BUSYBOX="busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
MS_VERSION=v0.9.1
MS_IMAGE="registry.k8s.io/metrics-server/metrics-server:v0.9.1@sha256:9b0ba1926e1d3089673f45461c3c1416109dea33b3ba3434048defd380df329b"

# 1. Repartir de rien.
# --ignore-not-found plutôt qu'un get préalable : un namespace encore en
# Terminating au moment du get disparaîtrait avant le delete (NotFound, set -e).
kubectl delete namespace atelier --ignore-not-found --wait=true --timeout=180s
for noeud in $(kubectl get nodes -o name); do
  kubectl taint nodes "${noeud#node/}" dedie- 2>/dev/null || true
  kubectl label "$noeud" dedie- 2>/dev/null || true
  kubectl label "$noeud" disque- 2>/dev/null || true
done

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

# 3. Le namespace et ses quatre applications.
kubectl create namespace atelier
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rendu
  namespace: atelier
spec:
  replicas: 1
  selector:
    matchLabels:
      app: rendu
  template:
    metadata:
      labels:
        app: rendu
    spec:
      containers:
        - name: rendu
          image: ${BUSYBOX}
          command: ["sleep", "infinity"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: accueil
  namespace: atelier
spec:
  replicas: 2
  selector:
    matchLabels:
      app: accueil
  template:
    metadata:
      labels:
        app: accueil
    spec:
      containers:
        - name: accueil
          image: ${BUSYBOX}
          command: ["sh", "-c", "mkdir -p /www && echo accueil > /www/index.html && exec httpd -f -p 8080 -h /www"]
          ports:
            - containerPort: 8080
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stockage
  namespace: atelier
spec:
  replicas: 1
  selector:
    matchLabels:
      app: stockage
  template:
    metadata:
      labels:
        app: stockage
    spec:
      containers:
        - name: stockage
          image: ${BUSYBOX}
          command: ["sleep", "infinity"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: galerie
  namespace: atelier
spec:
  replicas: 2
  selector:
    matchLabels:
      app: galerie
  template:
    metadata:
      labels:
        app: galerie
    spec:
      containers:
        - name: galerie
          image: ${BUSYBOX}
          command: ["sh", "-c", "mkdir -p /www && echo galerie > /www/index.html && exec httpd -f -p 8080 -h /www"]
          ports:
            - containerPort: 8080
EOF
kubectl -n atelier rollout status deployment/rendu deployment/accueil deployment/stockage deployment/galerie \
  --timeout=240s

# 4. metrics-server mesure-t-il les Pods ? Sans mesure, le HPA de l'apprenant
#    n'aurait rien à lire, et l'erreur ne serait pas la sienne.
for _ in $(seq 1 30); do
  if kubectl top pods -n atelier --no-headers 2>/dev/null | grep -q '^accueil-'; then
    break
  fi
  sleep 5
done
kubectl top pods -n atelier --no-headers
echo "Situation posée : atelier sans placement, sans plafond ni valeurs par défaut, sans HPA."
