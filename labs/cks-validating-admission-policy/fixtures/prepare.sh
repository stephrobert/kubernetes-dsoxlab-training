#!/usr/bin/env bash
# Pose la situation : un namespace qui accepte tout.
#
# Il n'y a presque rien a poser, et c'est voulu : ce lab ne repare pas un objet
# casse, il fait constater ce qu'un cluster nu admet. Une application y tourne,
# EPINGLEE par son digest, pour que le candidat voie que sa politique ne doit
# pas la faire tomber.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

# Ce que le candidat doit produire est retire s'il traine d'un passage
# precedent : sans cela, le lab rendrait 100 avant le travail.
kubectl get validatingadmissionpolicybinding -o name 2>/dev/null \
  | grep -vE 'safe-upgrades' | xargs -r kubectl delete --ignore-not-found || true
kubectl get validatingadmissionpolicy -o name 2>/dev/null \
  | grep -vE 'safe-upgrades' | xargs -r kubectl delete --ignore-not-found || true

if [[ "$(kubectl get namespace production -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/production --timeout=180s
fi
kubectl get namespace production >/dev/null 2>&1 || kubectl create namespace production

kubectl -n production delete pod conforme --ignore-not-found --wait=true
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: conforme
  namespace: production
spec:
  containers:
    - name: appli
      image: busybox@sha256:ab33eacc8251e3807b85bb6dba570e4698c3998eca6f0fc2ccb60575a563ea74
      command: ["sh", "-c", "sleep 86400"]
YAML

kubectl -n production wait --for=condition=ready pod/conforme --timeout=300s

# On montre l'etat de depart dans le journal : une image par tag passe.
kubectl -n production run sonde-depart --image=busybox:1.37 --restart=Never \
  --command -- sh -c 'sleep 5' >/dev/null 2>&1 \
  && echo "une image par TAG est ACCEPTEE" || echo "refusee"
kubectl -n production delete pod sonde-depart --ignore-not-found --wait=false >/dev/null 2>&1 || true
echo "Situation posee : le cluster accepte n'importe quelle image."
