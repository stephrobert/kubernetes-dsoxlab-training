#!/usr/bin/env bash
# Pose l'examen blanc CKAD sur le cluster kubeadm du catalogue :
#
#   - aucun contexte : chaque tâche désigne son hôte et son namespace (D63),
#     la mécanique vit dans shared/examen-ssh.yml ;
#   - ~/examen/ : le manifeste hérité de la tâche 8 et l'arbre Kustomize ;
#   - l'état de départ de chaque tâche, faux par construction.
#
# Rejouable : les namespaces sont attendus s'ils se terminent, puis recréés.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
FIX=/var/lib/dsoxlab/ckad-examen
NGINX="nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
NGINX_1306="nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703"
ECHO="hashicorp/http-echo:1.0.0@sha256:fcb75f691c8b0414d670ae570240cbf95502cc18a9ba57e982ecac589760a186"
BUSYBOX="busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"

for ns in atelier boutique securite; do
  if [[ "$(kubectl get namespace "$ns" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
    kubectl wait --for=delete "namespace/$ns" --timeout=240s
  fi
  kubectl get namespace "$ns" >/dev/null 2>&1 || kubectl create namespace "$ns"
done

rm -rf "${LAB_HOME}/examen"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/examen"
cp "$FIX/pdb-ancien.yaml" "${LAB_HOME}/examen/"
cp -r "$FIX/kustomize" "${LAB_HOME}/examen/"
chown -R "$LAB_USER:$LAB_USER" "${LAB_HOME}/examen"

cat <<YAML | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: atelier
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: web
          image: ${NGINX}
---
apiVersion: v1
kind: Pod
metadata:
  name: outil
  namespace: atelier
spec:
  containers:
    - name: shell
      image: busybox:1.38.0-inexistant
      command: ["sleep", "infinity"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitrine-bleu
  namespace: boutique
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vitrine
      version: bleu
  template:
    metadata:
      labels:
        app: vitrine
        version: bleu
    spec:
      containers:
        - name: web
          image: ${NGINX}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitrine-vert
  namespace: boutique
spec:
  replicas: 0
  selector:
    matchLabels:
      app: vitrine
      version: vert
  template:
    metadata:
      labels:
        app: vitrine
        version: vert
    spec:
      containers:
        - name: web
          image: ${NGINX_1306}
---
apiVersion: v1
kind: Service
metadata:
  name: vitrine
  namespace: boutique
spec:
  selector:
    app: vitrine
    version: bleu
  ports:
    - port: 80
      targetPort: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: catalogue
  namespace: boutique
spec:
  replicas: 3
  selector:
    matchLabels:
      app: catalogue
  template:
    metadata:
      labels:
        app: catalogue
    spec:
      containers:
        - name: web
          image: ${NGINX}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stock
  namespace: boutique
spec:
  replicas: 2
  selector:
    matchLabels:
      app: stock
  template:
    metadata:
      labels:
        app: stock
    spec:
      containers:
        - name: echo
          image: ${ECHO}
          args: ["-text=stock", "-listen=:5678"]
---
apiVersion: v1
kind: Service
metadata:
  name: stock
  namespace: boutique
spec:
  selector:
    app: stocks
  ports:
    - port: 80
      targetPort: 8080
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: infos
  namespace: boutique
spec:
  replicas: 1
  selector:
    matchLabels:
      app: infos
  template:
    metadata:
      labels:
        app: infos
    spec:
      containers:
        - name: echo
          image: ${ECHO}
          args: ["-text=infos", "-listen=:5678"]
---
apiVersion: v1
kind: Service
metadata:
  name: infos
  namespace: boutique
spec:
  selector:
    app: infos
  ports:
    - port: 80
      targetPort: 5678
---
apiVersion: v1
kind: Pod
metadata:
  name: interne
  namespace: boutique
  labels:
    app: interne
spec:
  containers:
    - name: echo
      image: ${ECHO}
      args: ["-text=interne", "-listen=:5678"]
      ports:
        - containerPort: 5678
---
apiVersion: v1
kind: Pod
metadata:
  name: front
  namespace: boutique
  labels:
    app: front
spec:
  containers:
    - name: shell
      image: ${BUSYBOX}
      command: ["sleep", "infinity"]
---
apiVersion: v1
kind: Pod
metadata:
  name: autre
  namespace: boutique
  labels:
    app: autre
spec:
  containers:
    - name: shell
      image: ${BUSYBOX}
      command: ["sleep", "infinity"]
YAML

kubectl -n atelier rollout status deployment/api --timeout=300s
kubectl -n boutique rollout status deployment/vitrine-bleu deployment/catalogue deployment/stock deployment/infos --timeout=300s
kubectl -n boutique wait --for=condition=Ready pod/interne pod/front pod/autre --timeout=240s

# La situation : tout le monde joint interne, stock n'a aucun endpoint.
IP_INTERNE="$(kubectl -n boutique get pod interne -o jsonpath='{.status.podIP}')"
kubectl -n boutique exec autre -- wget -qO- -T 5 "http://${IP_INTERNE}:5678/"
test -z "$(kubectl -n boutique get endpointslices -l kubernetes.io/service-name=stock \
  -o jsonpath='{.items[*].endpoints[*].addresses[*]}')"
echo "Examen posé : trois namespaces, les pannes en place."
