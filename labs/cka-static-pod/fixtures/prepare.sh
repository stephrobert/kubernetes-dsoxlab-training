#!/usr/bin/env bash
# Le setup a retiré le manifeste du worker ; le kubelet retire alors le Pod
# miroir de l'API, mais pas instantanément. On l'attend, sinon un check
# lancé aussitôt verrait le Pod d'un passage précédent. Un Pod nommé
# static-web posé par kubectl run, qui n'est pas un Pod statique, part aussi.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

kubectl -n default delete pod static-web --ignore-not-found --wait=false

for essai in $(seq 1 30); do
  if ! kubectl -n default get pod static-web-k8s-w1.lab >/dev/null 2>&1; then
    break
  fi
  sleep 3
done
kubectl -n default get pods
echo "Aucun Pod statique sur k8s-w1.lab : à l'apprenant de le poser."
