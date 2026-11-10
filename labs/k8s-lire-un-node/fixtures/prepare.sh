#!/usr/bin/env bash
# Pose la fiche à compléter, ~/lire-un-node/fiche.txt, après avoir vérifié que
# le worker désigné existe et est Ready. Ne crée aucun objet dans le cluster,
# ne touche ni aux Nodes ni à kube-system. Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
kubectl wait --for=condition=Ready node/architecture-worker2 --timeout=180s

install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/lire-un-node"
cat > "${LAB_HOME}/lire-un-node/fiche.txt" <<'FICHE'
# Fiche du Node architecture-worker2, telle que le Node la déclare.
# Card of the Node architecture-worker2, as the Node declares it.
# Les lignes qui commencent par # sont ignorées. Lines starting with # are ignored.

runtime:
version-kubelet:
cpu:
memoire:
condition-ready:
FICHE
chown "$LAB_USER:$LAB_USER" "${LAB_HOME}/lire-un-node/fiche.txt"
echo "Situation posée : fiche d'architecture-worker2 à compléter."
