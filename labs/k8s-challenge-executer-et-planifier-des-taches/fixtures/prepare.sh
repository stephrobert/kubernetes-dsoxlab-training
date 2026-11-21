#!/usr/bin/env bash
# Pose la situation du challenge : le namespace compta, une ConfigMap lots
# (une clé lot-<index> par lot, leur nombre tiré entre 3 et 6), une ConfigMap
# export-config (une période tirée au sort), et un Job export-compta qui a
# échoué faute de recevoir cette configuration.
#
# Le nombre de lots, leurs noms et la période changent à chaque préparation :
# la réponse ne se recopie pas d'une session à l'autre. La mémoire garde aussi
# l'UID du Job en échec, pour que les tests exigent qu'il ait été recréé.
#
# Rejouable : le namespace est recréé à neuf.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NS=compta
MEMOIRE=/var/lib/dsoxlab/challenge-executer-et-planifier-des-taches.json
BUSYBOX="busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"

if [[ "$(kubectl get namespace "$NS" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete "namespace/$NS" --timeout=180s
fi
kubectl delete namespace "$NS" --ignore-not-found --wait=true --timeout=180s
kubectl create namespace "$NS"

NOMBRE=$(( 3 + RANDOM % 4 ))
LOTS=()
ARGS=()
for (( i = 0; i < NOMBRE; i++ )); do
  NOM="lot-$(head -c 3 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  LOTS+=("$NOM")
  ARGS+=("--from-literal=lot-${i}=${NOM}")
done
kubectl create configmap lots -n "$NS" "${ARGS[@]}"

MOIS=$(( 1 + RANDOM % 12 ))
PERIODE=$(printf '2026-%02d' "$MOIS")
kubectl create configmap export-config -n "$NS" --from-literal=PERIODE="$PERIODE"

cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: export-compta
  namespace: $NS
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: export
          image: $BUSYBOX
          command:
            - sh
            - -c
            - |
              if [ -z "\$PERIODE" ]; then
                echo "PERIODE absente : rien a exporter"
                exit 2
              fi
              echo "export de la periode \$PERIODE"
EOF
kubectl wait --for=condition=Failed job/export-compta -n "$NS" --timeout=180s
UID_EXPORT=$(kubectl get job export-compta -n "$NS" -o jsonpath='{.metadata.uid}')

install -d -m 0755 /var/lib/dsoxlab
python3 - "$MEMOIRE" "$PERIODE" "$UID_EXPORT" "${LOTS[@]}" <<'PY'
import json
import sys

chemin, periode, uid, *lots = sys.argv[1:]
with open(chemin, "w") as f:
    json.dump({"lots": lots, "periode": periode, "uid_export": uid}, f)
PY
chmod 0600 "$MEMOIRE"

kubectl get configmaps,jobs -n "$NS"
echo "Situation posée : ${NOMBRE} lots, export-compta en échec."
