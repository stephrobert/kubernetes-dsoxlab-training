#!/usr/bin/env bash
# Pose l'état hérité de l'épreuve k8s-epreuve-reseau-avance, sur le cluster
# net-* que le setup vient de ramener aux valeurs du socle (Cilium 1.20.5 :
# Gateway API, chiffrement et proxy L7 au repos, aucune politique).
#
# - Les CRD de la Gateway API sont RETIRÉES s'il en reste : l'apprenant les
#   installe. Le setup a ramené Cilium au socle AVANT, dans cet ordre : retirer
#   les CRD pendant que gatewayAPI est actif rend la release Helm illisible
#   (mesuré le 2026-11-18).
# - Une CA propre à l'épreuve, et le certificat de vitrine.formation.test
#   qu'elle signe, rangé dans le Secret TLS vitrine-tls de boutique. La CA est
#   publiée dans la ConfigMap ca-boutique.
# - boutique : la vitrine (sur net-w2.lab), le client légitime caisse et le
#   Pod publicite (sur net-w1.lab), et relance, un client en boucle qui porte
#   les mêmes étiquettes que caisse et envoie, en plus d'un GET /, une requête
#   tirée au hasard que la politique demandée refusera.
#
# Rien de ce que l'apprenant doit produire n'existe. Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

ECHO="hashicorp/http-echo:1.0.0@sha256:fcb75f691c8b0414d670ae570240cbf95502cc18a9ba57e982ecac589760a186"
CURL="curlimages/curl:8.17.0@sha256:935d9100e9ba842cdb060de42472c7ca90cfe9a7c96e4dacb55e79e560b3ff40"
GWAPI=https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.3/standard-install.yaml

# Ce qu'un passage précédent a laissé.
kubectl delete namespace boutique --ignore-not-found --wait=true --timeout=180s
kubectl delete ciliumloadbalancerippools.cilium.io --all --ignore-not-found 2>/dev/null || true
kubectl delete gatewayclass cilium --ignore-not-found 2>/dev/null || true
kubectl delete -f "$GWAPI" --ignore-not-found > /dev/null

# La CA de l'épreuve et le certificat de la vitrine.
T=$(mktemp -d)
openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj "/CN=CA de l'epreuve reseau avance" \
  -keyout "$T/ca.key" -out "$T/ca.crt" 2> /dev/null
openssl req -newkey rsa:2048 -nodes -subj "/CN=vitrine.formation.test" \
  -keyout "$T/vitrine.key" -out "$T/vitrine.csr" 2> /dev/null
printf 'subjectAltName=DNS:vitrine.formation.test\n' > "$T/ext.cnf"
openssl x509 -req -in "$T/vitrine.csr" -CA "$T/ca.crt" -CAkey "$T/ca.key" -CAcreateserial -days 30 \
  -extfile "$T/ext.cnf" -out "$T/vitrine.crt" 2> /dev/null

kubectl create namespace boutique
kubectl -n boutique create secret tls vitrine-tls --cert="$T/vitrine.crt" --key="$T/vitrine.key"
kubectl -n boutique create configmap ca-boutique --from-file=ca.crt="$T/ca.crt"
rm -rf "$T"

# La requête que relance envoie en plus de GET / : tirée au hasard, et passée
# encodée pour qu'elle ne se lise pas d'un coup d'œil sur le Pod.
METHODES=(DELETE PUT POST PATCH)
CHEMINS=(/panier /stock /remboursement /promotions)
METHODE=${METHODES[$((RANDOM % 4))]}
CHEMIN=${CHEMINS[$((RANDOM % 4))]}
BOUCLE="while true; do curl -s -o /dev/null http://vitrine/; curl -s -o /dev/null -X $METHODE http://vitrine$CHEMIN; sleep 2; done"
BOUCLE_B64=$(printf '%s' "$BOUCLE" | base64 -w0)

kubectl apply -f - <<YAML
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
      nodeSelector:
        kubernetes.io/hostname: net-w2.lab
      containers:
        - name: vitrine
          image: "$ECHO"
          args: ["-text=vitrine", "-listen=:5678"]
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
---
apiVersion: v1
kind: Pod
metadata:
  name: caisse
  namespace: boutique
  labels: {app: caisse}
spec:
  nodeName: net-w1.lab
  containers:
    - {name: c, image: "$CURL", command: [sleep, "36000"]}
---
apiVersion: v1
kind: Pod
metadata:
  name: publicite
  namespace: boutique
  labels: {app: publicite}
spec:
  nodeName: net-w1.lab
  containers:
    - {name: c, image: "$CURL", command: [sleep, "36000"]}
---
apiVersion: v1
kind: Pod
metadata:
  name: relance
  namespace: boutique
  labels: {app: caisse}
spec:
  nodeName: net-w1.lab
  containers:
    - name: c
      image: "$CURL"
      command: [sh, -c, 'eval "\$(echo $BOUCLE_B64 | base64 -d)"']
YAML

kubectl -n boutique rollout status deployment/vitrine --timeout=180s
kubectl -n boutique wait --for=condition=Ready pod/caisse pod/publicite pod/relance --timeout=180s
# Pod prêt ne veut pas dire backend inscrit : juste après un redémarrage des
# agents Cilium, la première requête peut être refusée (curl 7, vu sur le lab
# k8s-filtrer-en-l7-avec-cilium le 2026-11-18). Une minute au plus.
for essai in $(seq 1 12); do
  if kubectl -n boutique exec caisse -- curl -s -m 5 http://vitrine/; then break; fi
  echo "la vitrine ne répond pas encore (essai ${essai})"
  sleep 5
done
kubectl -n boutique exec caisse -- curl -s -m 5 http://vitrine/
echo "État hérité posé : aucune Gateway, aucune politique, chiffrement éteint."
