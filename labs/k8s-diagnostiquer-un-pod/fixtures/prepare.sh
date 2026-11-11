#!/usr/bin/env bash
# Pose la situation du lab sur le cluster kind « boutique » :
#
#   - le namespace pods-en-panne, neuf, avec deux Pods nus en panne, ceux de la
#     démonstration de la leçon : image-fausse, sur un tag qui n'existe pas, et
#     plante, dont le conteneur sort en code 1 ;
#   - la mémoire de l'état initial, lisible par root seul : l'uid de
#     image-fausse, pour constater que son image a été corrigée EN PLACE ;
#   - le relevé à compléter, ~/pods-en-panne/releve.txt.
#
# Ne touche ni aux Nodes, ni à kube-system, ni aux namespaces des autres labs.
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
NS=pods-en-panne
BUSYBOX="busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
MEMOIRE=/var/lib/dsoxlab/diagnostiquer-un-pod.json

# --ignore-not-found plutôt qu'un get préalable : un namespace encore en
# Terminating au moment du get disparaîtrait avant le delete (NotFound, set -e).
kubectl delete namespace "$NS" --ignore-not-found --wait=true --timeout=180s
kubectl create namespace "$NS"
kubectl -n "$NS" run image-fausse --image=nginx:1.30.999
kubectl -n "$NS" run plante --image="$BUSYBOX" \
  -- sh -c 'echo "je démarre puis je plante"; exit 1'

# Le code de sortie ne se lit qu'une fois le conteneur arrêté au moins une fois.
for _ in $(seq 1 60); do
  code="$(kubectl -n "$NS" get pod plante \
    -o jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}{.status.containerStatuses[0].state.terminated.exitCode}')"
  [ -n "$code" ] && break
  sleep 2
done

install -d -m 0700 /var/lib/dsoxlab
uid="$(kubectl -n "$NS" get pod image-fausse -o jsonpath='{.metadata.uid}')"
printf '{"image-fausse": "%s"}\n' "$uid" > "$MEMOIRE"
chmod 0600 "$MEMOIRE"

install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/${NS}"
cat > "${LAB_HOME}/${NS}/releve.txt" <<'RELEVE'
# Ce que vous lisez dans le cluster, une valeur par clé.
# What you read in the cluster, one value per key.
# Les lignes qui commencent par # sont ignorées. Lines starting with # are ignored.

raison-image-fausse:
code-sortie-plante:
RELEVE
chown "$LAB_USER:$LAB_USER" "${LAB_HOME}/${NS}/releve.txt"
echo "Situation posée : image-fausse et plante en panne, image-fausse ${uid}."
