#!/usr/bin/env bash
# Pose la situation du challenge dans comptoir, plus un rôdeur dans voisinage :
#
# - catalogue et panier servent leur nom, chacun derrière son Service, mais
#   aucune route ne les expose ;
# - le Service ancien, hérité, ne trouve aucun Pod (son sélecteur exige un
#   label que les Pods n'ont pas) et vise un port où rien n'écoute ;
# - le Pod sonde interroge un serveur DNS qui n'existe pas ;
# - la base, le backend, le frontend et le rôdeur se joignent tous, faute de
#   la moindre politique.
#
# Avant de rendre la main, le script mesure que la situation est bien celle-là.
# Rejouable : les namespaces sont attendus s'ils se terminent, les politiques
# et la route d'un passage précédent sont retirées, les Pods sont recréés.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

for ns in comptoir voisinage; do
  if [[ "$(kubectl get namespace "$ns" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
    kubectl wait --for=delete "namespace/$ns" --timeout=180s
  fi
  kubectl get namespace "$ns" >/dev/null 2>&1 || kubectl create namespace "$ns"
done
kubectl -n comptoir delete networkpolicy --all
kubectl -n comptoir delete ingress --all
kubectl -n comptoir delete httproute,gateway --all --ignore-not-found
# Un Pod garde sa configuration DNS : sonde doit repartir cassée.
kubectl -n comptoir delete pod sonde --ignore-not-found --wait=true

cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: catalogue
  namespace: comptoir
spec:
  replicas: 1
  selector:
    matchLabels:
      app: catalogue
  template:
    metadata:
      labels:
        app: catalogue
    spec:
      containers:
        - name: app
          image: hashicorp/http-echo:1.0.0@sha256:fcb75f691c8b0414d670ae570240cbf95502cc18a9ba57e982ecac589760a186
          args: ["-text=catalogue", "-listen=:5678"]
          ports:
            - containerPort: 5678
---
apiVersion: v1
kind: Service
metadata:
  name: catalogue
  namespace: comptoir
spec:
  selector:
    app: catalogue
  ports:
    - port: 80
      targetPort: 5678
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: panier
  namespace: comptoir
spec:
  replicas: 1
  selector:
    matchLabels:
      app: panier
  template:
    metadata:
      labels:
        app: panier
    spec:
      containers:
        - name: app
          image: hashicorp/http-echo:1.0.0@sha256:fcb75f691c8b0414d670ae570240cbf95502cc18a9ba57e982ecac589760a186
          args: ["-text=panier", "-listen=:5678"]
          ports:
            - containerPort: 5678
---
apiVersion: v1
kind: Service
metadata:
  name: panier
  namespace: comptoir
spec:
  selector:
    app: panier
  ports:
    - port: 80
      targetPort: 5678
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ancien
  namespace: comptoir
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ancien
  template:
    metadata:
      labels:
        app: ancien
    spec:
      containers:
        - name: web
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          ports:
            - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: ancien
  namespace: comptoir
spec:
  selector:
    app: ancien
    version: v1
  ports:
    - port: 80
      targetPort: 8080
---
apiVersion: v1
kind: Pod
metadata:
  name: sonde
  namespace: comptoir
  labels:
    app: sonde
spec:
  dnsPolicy: "None"
  dnsConfig:
    nameservers:
      - 192.0.2.53
    searches:
      - comptoir.svc.cluster.local
      - svc.cluster.local
      - cluster.local
  containers:
    - name: shell
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "infinity"]
---
apiVersion: v1
kind: Pod
metadata:
  name: base
  namespace: comptoir
  labels:
    app: base
spec:
  containers:
    - name: postgres
      image: postgres:18.6-alpine@sha256:9ba53c7d41ea093baf5c1ba635ba5434c4f979880527d49bb7d9237d3193085b
      env:
        - name: POSTGRES_PASSWORD
          value: lab-seulement
      ports:
        - containerPort: 5432
---
apiVersion: v1
kind: Service
metadata:
  name: base
  namespace: comptoir
spec:
  selector:
    app: base
  ports:
    - port: 5432
      targetPort: 5432
---
apiVersion: v1
kind: Pod
metadata:
  name: backend
  namespace: comptoir
  labels:
    app: backend
spec:
  containers:
    - name: shell
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "infinity"]
---
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  namespace: comptoir
  labels:
    app: frontend
spec:
  containers:
    - name: shell
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "infinity"]
---
apiVersion: v1
kind: Pod
metadata:
  name: rodeur
  namespace: voisinage
  labels:
    app: backend
spec:
  containers:
    - name: shell
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "infinity"]
EOF

kubectl -n comptoir rollout status deployment/catalogue deployment/panier deployment/ancien --timeout=240s
kubectl -n comptoir wait --for=condition=Ready pod/sonde pod/base pod/backend pod/frontend --timeout=240s
kubectl -n voisinage wait --for=condition=Ready pod/rodeur --timeout=120s

# La situation : tout le monde atteint la base. Postgres met quelques
# secondes à écouter après Ready.
for essai in $(seq 1 20); do
  if kubectl -n comptoir exec backend -- nc -z -w 3 base 5432; then
    break
  fi
  sleep 3
done
kubectl -n comptoir exec backend -- nc -z -w 3 base 5432
kubectl -n comptoir exec frontend -- nc -z -w 3 base 5432
kubectl -n voisinage exec rodeur -- nc -z -w 3 base.comptoir.svc.cluster.local 5432

# Le Service ancien ne trouve aucun Pod, et sonde ne résout rien.
test -z "$(kubectl -n comptoir get endpointslices -l kubernetes.io/service-name=ancien \
  -o jsonpath='{.items[*].endpoints[*].addresses[*]}')"
if kubectl -n comptoir exec sonde -- nslookup catalogue.comptoir.svc.cluster.local; then
  echo "sonde résout encore : la situation n'est pas celle du scénario" >&2
  exit 1
fi
echo "Situation posée : rien n'est exposé, ancien est vide, sonde ne résout rien, la base est ouverte à tous."
