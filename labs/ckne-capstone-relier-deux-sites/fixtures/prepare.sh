#!/usr/bin/env bash
# Pose la situation du capstone ckne-capstone-relier-deux-sites, depuis
# ha-cp1.lab (kubeconfig du site 2 posé par le setup), sur deux clusters neufs :
#
# - site 1 : l'autorité interne de cert-manager, le ClusterIssuer
#   autorite-des-sites (amorce auto-signée, certificat d'autorité dans le
#   namespace cert-manager, puis ClusterIssuer de type CA) ;
# - dans chaque site, le namespace boutique, le Deployment vitrine qui répond
#   par le nom de SON site, et un Service vitrine ORDINAIRE ;
# - site 1 seulement : le Pod client, et le Service interne, de type
#   LoadBalancer, qui ne doit jamais être annoncé au réseau.
#
# Rien de ce que l'apprenant doit produire n'existe : sites non reliés, aucun
# Service global, aucun pool d'adresses, aucun objet BGP, aucune Gateway, aucun
# certificat. Le setup a remis les nœuds à zéro avant.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

ECHO="hashicorp/http-echo:1.0.0@sha256:fcb75f691c8b0414d670ae570240cbf95502cc18a9ba57e982ecac589760a186"
CURL="curlimages/curl:8.17.0@sha256:935d9100e9ba842cdb060de42472c7ca90cfe9a7c96e4dacb55e79e560b3ff40"
BUSYBOX="busybox:1.37@sha256:a7dbc319b1438115a207e11930dc4bb3e643dcb3ec0bdd694bb36cd8fad289ec"
declare -A KUBECONFIGS=([1]=/etc/kubernetes/admin.conf [2]=/etc/kubernetes/cluster-2.conf)
K1="kubectl --kubeconfig ${KUBECONFIGS[1]}"

# --- L'autorité interne du site 1 ---------------------------------------------
# Le webhook de cert-manager peut refuser quelques secondes après son
# démarrage : on réessaie.
for essai in $(seq 1 30); do
  if $K1 apply -f - <<'YAML'
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: amorce-auto-signee
spec:
  selfSigned: {}
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: autorite-des-sites
  namespace: cert-manager
spec:
  isCA: true
  commonName: Autorite des sites
  subject:
    organizations:
      - Formation Kubernetes
  secretName: autorite-des-sites
  duration: 8760h
  privateKey:
    algorithm: ECDSA
    size: 256
  issuerRef:
    name: amorce-auto-signee
    kind: ClusterIssuer
    group: cert-manager.io
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: autorite-des-sites
spec:
  ca:
    secretName: autorite-des-sites
YAML
  then break; fi
  echo "webhook de cert-manager pas encore prêt (essai ${essai})"
  sleep 5
done
$K1 -n cert-manager wait --for=condition=Ready certificate/autorite-des-sites --timeout=180s
$K1 wait --for=condition=Ready clusterissuer/autorite-des-sites --timeout=180s

# --- La vitrine, dans chaque site -------------------------------------------------
for id in 1 2; do
  k="kubectl --kubeconfig ${KUBECONFIGS[$id]}"
  $k create namespace boutique
  $k apply -f - <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitrine
  namespace: boutique
spec:
  replicas: 1
  selector:
    matchLabels: {app: vitrine}
  template:
    metadata:
      labels: {app: vitrine}
    spec:
      containers:
        - name: vitrine
          image: "$ECHO"
          args: ["-text=vitrine-site-$id", "-listen=:5678"]
          ports:
            - containerPort: 5678
---
apiVersion: v1
kind: Service
metadata:
  name: vitrine
  namespace: boutique
spec:
  selector: {app: vitrine}
  ports:
    - {name: http, port: 80, targetPort: 5678}
YAML
  $k -n boutique rollout status deployment/vitrine --timeout=240s
done

# --- Site 1 : le client, et le Service interne à ne jamais annoncer -----------
$K1 apply -f - <<YAML
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: boutique
  labels: {app: client}
spec:
  containers:
    - {name: c, image: "$CURL", command: [sleep, "36000"]}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: interne
  namespace: boutique
spec:
  replicas: 1
  selector:
    matchLabels: {app: interne}
  template:
    metadata:
      labels: {app: interne}
    spec:
      containers:
        - name: interne
          image: "$BUSYBOX"
          command: [sh, -c, 'mkdir -p /www && echo interne > /www/index.html && exec httpd -f -p 8080 -h /www']
          ports:
            - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: interne
  namespace: boutique
spec:
  type: LoadBalancer
  selector: {app: interne}
  ports:
    - {name: http, port: 80, targetPort: 8080}
YAML
$K1 -n boutique wait --for=condition=Ready pod/client --timeout=180s
$K1 -n boutique rollout status deployment/interne --timeout=180s

# --- Constat de départ : la vitrine ne répond que du site 1 ------------------------
for i in 1 2 3; do $K1 -n boutique exec client -- curl -s -m 5 http://vitrine.boutique/ || true; done
$K1 -n boutique get service interne
echo "Situation posée : deux sites non reliés, aucune annonce, aucune Gateway."
