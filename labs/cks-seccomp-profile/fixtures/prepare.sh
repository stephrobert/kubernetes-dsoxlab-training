#!/usr/bin/env bash
# Pose la situation : un namespace vide, et un nœud qui ne connaît aucun
# profil seccomp local.
#
# Le répertoire des profils locaux du kubelet est créé ici, VIDE. C'est
# délibéré : sans lui, le candidat qui dépose son profil au bon endroit
# recevrait quand même une erreur de montage, et passerait son temps à
# chercher une faute qui n'est pas la sienne. Le kubelet ne crée pas ce
# répertoire, il s'attend à le trouver.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne rend que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

SECCOMP_DIR=/var/lib/kubelet/seccomp/profiles
mkdir -p "$SECCOMP_DIR"

if [[ "$(kubectl get namespace confinement -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/confinement --timeout=180s
fi
kubectl get namespace confinement >/dev/null 2>&1 || kubectl create namespace confinement

# Ce que le candidat doit produire est retiré s'il traîne d'un passage
# précédent : le Pod, et surtout le PROFIL. Un profil laissé sur le nœud
# ferait passer le premier test avant tout travail.
kubectl -n confinement delete pod seccomp-pod --ignore-not-found --wait=true
rm -f "${SECCOMP_DIR}/restrict-chmod.json"

# Un Pod témoin, SANS profil, qui montre l'état de départ : il peut appeler
# chmod, comme n'importe quel conteneur par défaut. C'est la référence à
# laquelle le candidat comparera son Pod confiné.
kubectl -n confinement delete pod temoin --ignore-not-found --wait=true
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: temoin
  namespace: confinement
spec:
  nodeName: k8s-cp.lab
  containers:
    - name: outil
      image: busybox:1.37
      command: ["sh", "-c", "sleep 86400"]
YAML
kubectl -n confinement wait --for=condition=ready pod/temoin --timeout=180s

echo "Situation posée : aucun profil local, et un témoin qui appelle chmod librement."
