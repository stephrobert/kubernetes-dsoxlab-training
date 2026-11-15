#!/usr/bin/env bash
# Pose la situation : une API et trois clients qui l'appellent toutes les deux
# secondes, et une NetworkPolicy qui en refuse un.
#
# L'API tourne sur net-w1.lab, les trois clients sur net-w2.lab : le refus
# traverse le réseau entre les deux workers, et c'est l'agent Cilium de
# net-w1.lab, celui du Pod de destination, qui le voit et le compte.
#
# Le client refusé est TIRÉ AU SORT à chaque passage, et seul root lit le nom
# retenu (/var/lib/dsoxlab-labs/). Un constat recopié d'un passage précédent,
# ou d'un camarade, n'a donc qu'une chance sur trois d'être juste.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne rend que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NS=magasin
REFERENCE=/var/lib/dsoxlab-labs/k8s-auditer-les-flux-avec-hubble.ref

# Un passage précédent est défait en entier, constat compris : sans cela, le
# lab rendrait des points avant le travail.
if kubectl get namespace magasin >/dev/null 2>&1; then
  kubectl delete namespace magasin --wait=true --timeout=180s
fi
kubectl create namespace magasin

REFUSE="$(shuf -n 1 -e vitrine panier compta)"
mkdir -p /var/lib/dsoxlab-labs
install -m 0600 /dev/null "$REFERENCE"
printf '%s\n' "$REFUSE" > "$REFERENCE"

kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: api
  namespace: magasin
  labels:
    app: api
spec:
  nodeName: net-w1.lab
  containers:
    - name: api
      image: nginx:1.30.6
      ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: magasin
spec:
  selector:
    app: api
  ports:
    - port: 80
      targetPort: 80
---
# Seuls les Pods qui portent acces-api=autorise entrent sur l'API, et
# seulement sur le port 80. Le reste du trafic entrant est refusé.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-entrant
  namespace: magasin
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              acces-api: autorise
      ports:
        - protocol: TCP
          port: 80
YAML

for client in vitrine panier compta; do
  if [[ "$client" == "$REFUSE" ]]; then
    acces=en-attente
  else
    acces=autorise
  fi
  kubectl apply -f - <<YAML
apiVersion: v1
kind: Pod
metadata:
  name: ${client}
  namespace: magasin
  labels:
    role: client
    acces-api: ${acces}
spec:
  nodeName: net-w2.lab
  containers:
    - name: client
      image: busybox:1.38.0
      command:
        - sh
        - -c
        - while true; do wget -q -T 2 -O /dev/null http://api.magasin.svc.cluster.local/ || true; sleep 2; done
YAML
done

kubectl -n "$NS" wait --for=condition=Ready pod --all --timeout=180s
