#!/usr/bin/env bash
# Pose la situation du lab k8s-imposer-des-regles-avec-gatekeeper.
#
#   - Gatekeeper n'est pas installe (on le retire s'il reste d'un passage
#     precedent) ;
#   - le namespace entrepot fait tourner ancien-stock, un Pod dont l'image vient
#     de Docker Hub : il existe AVANT toute regle, seul l'audit peut le voir ;
#   - le namespace entrepot-temoin sert a verifier que la regle ne deborde pas.
#
# Etat de depart releve le 2026-11-23 sur kubeadm v1.37.2.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

# Depose par setup.yaml : ansible.builtin.script ne copie que le script appele.
bash /var/lib/dsoxlab/retirer-gatekeeper.sh

for ns in entrepot entrepot-temoin; do
  if [[ "$(kubectl get namespace "$ns" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
    kubectl wait --for=delete "namespace/$ns" --timeout=180s
  fi
  kubectl get namespace "$ns" >/dev/null 2>&1 || kubectl create namespace "$ns"
done

kubectl -n entrepot delete pod ancien-stock --ignore-not-found --wait=true
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: ancien-stock
  namespace: entrepot
spec:
  containers:
    - name: appli
      image: docker.io/library/busybox:1.37
      command: ["sh", "-c", "sleep 86400"]
YAML
kubectl -n entrepot wait --for=condition=ready pod/ancien-stock --timeout=300s
echo "Situation posee : pas de Gatekeeper, ancien-stock tourne depuis Docker Hub."
