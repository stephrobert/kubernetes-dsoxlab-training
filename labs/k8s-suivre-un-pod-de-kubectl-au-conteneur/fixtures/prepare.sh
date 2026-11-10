#!/usr/bin/env bash
# Pose la situation du lab sur le cluster partagé « architecture » : un
# namespace suivre-un-pod neuf et vide, et le relevé à compléter. Le
# Deployment, c'est l'apprenant qui le crée. Ne touche ni aux Nodes ni à
# kube-system. Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"

if kubectl get namespace suivre-un-pod >/dev/null 2>&1; then
  kubectl delete namespace suivre-un-pod --wait=true --timeout=180s
fi
kubectl create namespace suivre-un-pod

install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/suivre-un-pod"
cat > "${LAB_HOME}/suivre-un-pod/etapes.txt" <<'RELEVE'
# Pour chaque étape, le composant qui a agi, lu dans les événements du Pod.
# For each step, the component that acted, read in the events of the Pod.
# Les lignes qui commencent par # sont ignorées. Lines starting with # are ignored.

scheduled:
pulled:
created:
started:

noeud-du-kubelet:
RELEVE
chown "$LAB_USER:$LAB_USER" "${LAB_HOME}/suivre-un-pod/etapes.txt"
echo "Situation posée : namespace suivre-un-pod vide, relevé à compléter."
