#!/usr/bin/env bash
# Pose la situation du challenge k8s-challenge-donnees-qui-survivent sur le
# cluster kind « lab » :
#
#   - le namespace archives, sans application ;
#   - journal-ancien, une revendication restée Pending : elle désigne une
#     StorageClass « rapide » qui n'existe pas. Son uid est mémorisé dans
#     /var/lib/dsoxlab/challenge-donnees-qui-survivent.json, pour dater une
#     éventuelle recréation ;
#   - ~/archives/, vide, où l'apprenant consigne la cause du Pending.
#
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
MEMOIRE=/var/lib/dsoxlab/challenge-donnees-qui-survivent.json

kubectl delete namespace archives --ignore-not-found --wait=true --timeout=180s
kubectl create namespace archives
kubectl apply -f - <<YAML
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: journal-ancien
  namespace: archives
spec:
  storageClassName: rapide
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 100Mi
YAML

# L'événement qui dit la cause : le contrôleur des volumes le pose dès qu'il
# examine la revendication.
for _ in $(seq 1 60); do
  if kubectl -n archives get events --field-selector involvedObject.name=journal-ancien -o name | grep -q .; then
    break
  fi
  sleep 2
done
test "$(kubectl -n archives get pvc journal-ancien -o jsonpath='{.status.phase}')" = Pending

install -d -m 0755 /var/lib/dsoxlab
printf '{"journal_uid": "%s"}\n' "$(kubectl -n archives get pvc journal-ancien -o jsonpath='{.metadata.uid}')" > "$MEMOIRE"

rm -rf "${LAB_HOME:?}/archives"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/archives"
echo "Situation posée : archives sans application, journal-ancien en Pending."
