#!/usr/bin/env bash
# Pose la partie « cluster » de la situation, avant que le setup ne casse le
# worker :
#
# - le namespace reseau et le Pod sonde, épinglé sur le control plane ;
# - deux Services à diagnostiquer, stock et archives. L'un n'a aucun endpoint,
#   et kube-proxy refuse aussitôt toute connexion vers lui. L'autre envoie vers
#   une adresse muette, 192.0.2.10 (bloc réservé à la documentation), où la
#   connexion attend jusqu'au délai. Lequel est lequel est TIRÉ AU SORT à chaque
#   préparation, et mémorisé pour les tests : le verdict ne se devine pas ;
# - le dossier de travail de l'apprenant, vide.
#
# Rejouable : le namespace est attendu s'il se termine, puis recréé.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
MEMOIRE=/var/lib/dsoxlab/troubleshoot-networking.json

if [[ "$(kubectl get namespace reseau -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/reseau --timeout=180s
fi
kubectl get namespace reseau >/dev/null 2>&1 || kubectl create namespace reseau

if (( RANDOM % 2 )); then
  REFUS=stock; DELAI=archives
else
  REFUS=archives; DELAI=stock
fi

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: sonde
  namespace: reseau
spec:
  nodeName: k8s-cp.lab
  containers:
    - name: shell
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "infinity"]
---
apiVersion: v1
kind: Service
metadata:
  name: ${REFUS}
  namespace: reseau
spec:
  selector:
    app: ${REFUS}
  ports:
    - port: 80
      targetPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: ${DELAI}
  namespace: reseau
spec:
  ports:
    - port: 80
      targetPort: 80
---
apiVersion: discovery.k8s.io/v1
kind: EndpointSlice
metadata:
  name: ${DELAI}-muet
  namespace: reseau
  labels:
    kubernetes.io/service-name: ${DELAI}
addressType: IPv4
ports:
  - port: 80
    protocol: TCP
endpoints:
  - addresses:
      - 192.0.2.10
EOF

kubectl -n reseau wait --for=condition=Ready pod/sonde --timeout=180s

install -d -m 0755 /var/lib/dsoxlab
printf '{"refus": "%s", "delai": "%s"}\n' "$REFUS" "$DELAI" > "$MEMOIRE"
chmod 0600 "$MEMOIRE"

rm -rf "${LAB_HOME}/reseau"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/reseau"

# La situation : l'un refuse aussitôt, l'autre attend. On le mesure, sinon le
# lab demanderait un verdict que le cluster ne permet pas de poser.
debut=$(date +%s)
if kubectl -n reseau exec sonde -- wget -qO- -T 5 "http://${REFUS}/"; then
  echo "${REFUS} répond : la situation n'est pas celle du scénario" >&2; exit 1
fi
duree_refus=$(( $(date +%s) - debut ))
debut=$(date +%s)
if kubectl -n reseau exec sonde -- wget -qO- -T 5 "http://${DELAI}/"; then
  echo "${DELAI} répond : la situation n'est pas celle du scénario" >&2; exit 1
fi
duree_delai=$(( $(date +%s) - debut ))
echo "refus en ${duree_refus} s, délai en ${duree_delai} s"
(( duree_refus <= 2 && duree_delai >= 4 ))
echo "Partie cluster posée : sonde sur le control plane, un refus, un délai."
