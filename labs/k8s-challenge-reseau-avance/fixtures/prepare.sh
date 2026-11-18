#!/usr/bin/env bash
# Pose la situation du challenge k8s-challenge-reseau-avance, sur le cluster
# net-* que le setup vient de ramener aux valeurs du socle, passerelle d'egress
# et masquage BPF activés (Cilium 1.20.5, sans kube-proxy, Hubble actif).
#
# Quatre situations, une par état demandé :
#
#   catalogue   le Service catalogue ne sert personne : son sélecteur
#               (app=catalogue-web) ne correspond à aucun Pod, les Pods du
#               Deployment portent app=catalogue. Un Pod client sur net-w1.
#   commandes   le Service stock, fermé par la NetworkPolicy refus-par-defaut
#               (tout l'entrant refusé). Dans boutique, panier (qui doit y
#               accéder) et robot (qui doit rester dehors).
#   facturation le Pod export sur net-w1, et l'URL du témoin. Aucune
#               passerelle désignée, aucune politique de sortie.
#   paiement    l'API sur net-w1, trois clients sur net-w2 qui l'appellent
#               toutes les deux secondes. L'API n'accepte que acces=autorise sur
#               le port 80. UN client est refusé, tiré au sort, et son motif
#               aussi : soit il porte acces=en-attente et appelle le port 80,
#               soit il porte acces=autorise et appelle le port 8080.
#
# La réponse attendue (jeton du catalogue, client refusé, port) est écrite
# dans un fichier lisible par root seul, sur le plan de contrôle. Rien de ce
# que l'apprenant doit produire n'existe. Rejouable : tout est défait d'abord.
#
# TEMOIN_URL est passée par le setup.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

BUSYBOX="busybox:1.37@sha256:a7dbc319b1438115a207e11930dc4bb3e643dcb3ec0bdd694bb36cd8fad289ec"
REFERENCE=/var/lib/dsoxlab-labs/k8s-challenge-reseau-avance.ref
NAMESPACES="catalogue commandes boutique facturation paiement"

# --- Défaire un passage précédent -------------------------------------------
kubectl delete ciliumegressgatewaypolicies.cilium.io --all --ignore-not-found --wait=true 2>/dev/null || true
for n in $(kubectl get nodes -o name); do kubectl label "$n" egress-gateway- 2>/dev/null || true; done
# shellcheck disable=SC2086
kubectl delete namespace $NAMESPACES --ignore-not-found --wait=true --timeout=300s
for ns in $NAMESPACES; do kubectl create namespace "$ns"; done

# --- La réponse attendue ------------------------------------------------------
JETON="catalogue-$(od -An -N6 -tx1 /dev/urandom | tr -d ' \n')"
REFUSE="$(shuf -n 1 -e client-a client-b client-c)"
MOTIF="$(shuf -n 1 -e etiquette port)"
if [[ "$MOTIF" == etiquette ]]; then PORT=80; else PORT=8080; fi
mkdir -p /var/lib/dsoxlab-labs
install -m 0600 /dev/null "$REFERENCE"
printf 'jeton=%s\nrefuse=%s\nport=%s\n' "$JETON" "$REFUSE" "$PORT" > "$REFERENCE"

# --- 1. catalogue : un Service qui ne sert personne ---------------------------
kubectl apply -f - <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: catalogue
  namespace: catalogue
spec:
  replicas: 2
  selector:
    matchLabels: {app: catalogue}
  template:
    metadata:
      labels: {app: catalogue}
    spec:
      containers:
        - name: web
          image: "$BUSYBOX"
          command: [sh, -c, 'mkdir -p /www && echo $JETON > /www/index.html && exec httpd -f -p 8080 -h /www']
          ports:
            - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: catalogue
  namespace: catalogue
spec:
  selector:
    app: catalogue-web
  ports:
    - port: 80
      targetPort: 8080
---
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: catalogue
  labels: {app: client}
spec:
  nodeName: net-w1.lab
  containers:
    - {name: c, image: "$BUSYBOX", command: [sleep, "36000"]}
YAML

# --- 2. commandes et boutique : un namespace fermé -----------------------------
kubectl apply -f - <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stock
  namespace: commandes
spec:
  replicas: 1
  selector:
    matchLabels: {app: stock}
  template:
    metadata:
      labels: {app: stock}
    spec:
      containers:
        - name: web
          image: "$BUSYBOX"
          command: [sh, -c, 'mkdir -p /www && echo stock > /www/index.html && exec httpd -f -p 80 -h /www']
          ports:
            - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: stock
  namespace: commandes
spec:
  selector: {app: stock}
  ports:
    - port: 80
      targetPort: 80
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: refus-par-defaut
  namespace: commandes
spec:
  podSelector: {}
  policyTypes: [Ingress]
---
apiVersion: v1
kind: Pod
metadata:
  name: panier
  namespace: boutique
  labels: {app: panier}
spec:
  containers:
    - {name: c, image: "$BUSYBOX", command: [sleep, "36000"]}
---
apiVersion: v1
kind: Pod
metadata:
  name: robot
  namespace: boutique
  labels: {app: robot}
spec:
  containers:
    - {name: c, image: "$BUSYBOX", command: [sleep, "36000"]}
YAML

# --- 3. facturation : une sortie sans passerelle -------------------------------
kubectl -n facturation create configmap temoin --from-literal=url="$TEMOIN_URL"
kubectl apply -f - <<YAML
apiVersion: v1
kind: Pod
metadata:
  name: export
  namespace: facturation
  labels: {app: export}
spec:
  nodeName: net-w1.lab
  containers:
    - {name: c, image: "$BUSYBOX", command: [sleep, "36000"]}
YAML

# --- 4. paiement : un client refusé, qui insiste --------------------------------
kubectl apply -f - <<YAML
apiVersion: v1
kind: Pod
metadata:
  name: api
  namespace: paiement
  labels: {app: api}
spec:
  nodeName: net-w1.lab
  containers:
    - name: web
      image: "$BUSYBOX"
      command: [sh, -c, 'mkdir -p /www && echo api > /www/index.html && httpd -p 8080 -h /www && exec httpd -f -p 80 -h /www']
      ports:
        - containerPort: 80
        - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: paiement
spec:
  selector: {app: api}
  ports:
    - {name: http, port: 80, targetPort: 80}
    - {name: admin, port: 8080, targetPort: 8080}
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-entrant
  namespace: paiement
spec:
  podSelector:
    matchLabels: {app: api}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels: {acces: autorise}
      ports:
        - {protocol: TCP, port: 80}
YAML
for client in client-a client-b client-c; do
  acces=autorise; port=80
  if [[ "$client" == "$REFUSE" ]]; then
    if [[ "$MOTIF" == etiquette ]]; then acces=en-attente; else port=8080; fi
  fi
  kubectl apply -f - <<YAML
apiVersion: v1
kind: Pod
metadata:
  name: ${client}
  namespace: paiement
  labels: {role: client, acces: ${acces}}
spec:
  nodeName: net-w2.lab
  containers:
    - name: c
      image: "$BUSYBOX"
      command: [sh, -c, 'while true; do wget -q -T 2 -O /dev/null http://api.paiement.svc.cluster.local:${port}/ || true; sleep 2; done']
YAML
done

for ns in $NAMESPACES; do kubectl -n "$ns" wait --for=condition=Ready pod --all --timeout=300s; done

# --- Constat de départ -----------------------------------------------------------
kubectl -n catalogue get endpointslice -l kubernetes.io/service-name=catalogue -o jsonpath='{.items[*].endpoints}'; echo
! kubectl -n boutique exec panier -- wget -qO- -T 3 http://stock.commandes/
kubectl -n facturation exec export -- wget -qO- -T 5 "$TEMOIN_URL/depart"
echo "Situation posée : refusé ${REFUSE}, port ${PORT}, témoin ${TEMOIN_URL}."
