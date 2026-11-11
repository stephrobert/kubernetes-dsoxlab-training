#!/usr/bin/env bash
# Pose la situation du lab sur le cluster kind « boutique » : ni equipe-api ni
# equipe-front, aucun objet api dans default, et le relevé à compléter,
# ~/namespaces/releve.txt. L'apprenant crée tout.
#
# Ne touche qu'à ses deux namespaces et aux objets api de default. Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"

# --ignore-not-found plutôt qu'un get préalable : un namespace encore en
# Terminating au moment du get disparaîtrait avant le delete (NotFound, set -e).
kubectl delete namespace equipe-api equipe-front --ignore-not-found --wait=true --timeout=180s
kubectl -n default delete deployment/api service/api --ignore-not-found

install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/namespaces"
cat > "${LAB_HOME}/namespaces/releve.txt" <<'RELEVE'
# Ce que vous observez depuis le Pod client, une valeur par clé.
# What you observe from the client Pod, one value per key.
# Les lignes qui commencent par # sont ignorées. Lines starting with # are ignored.

reponse-nom-qualifie:
nom-court:
RELEVE
chown "$LAB_USER:$LAB_USER" "${LAB_HOME}/namespaces/releve.txt"
echo "Situation posée : aucun namespace equipe-api ni equipe-front."
