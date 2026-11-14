#!/usr/bin/env bash
# Pose la DERNIÈRE panne du setup : un flag mal orthographié dans le manifeste
# statique de l'API server (repris de cka-troubleshoot-apiserver). Elle vient
# en dernier parce qu'après elle, plus aucune commande kubectl ne passe : tout
# ce qui se pose ou s'attend par l'API doit être fait avant.
#
# Le manifeste sain est d'abord copié hors de /etc/kubernetes/manifests (le
# kubelet lancerait tout fichier posé là) : cleanup.yaml le remet tel quel,
# quoi que l'apprenant en ait fait, puis supprime la copie.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare-api-server.log) 2>&1
set -x

MANIFESTE=/etc/kubernetes/manifests/kube-apiserver.yaml
COPIE=/var/lib/dsoxlab/depanner-kube-apiserver.yaml
BON='--authorization-mode='
FAUX='--authorization-modes='

grep -q -- "${BON}Node,RBAC" "$MANIFESTE" || {
  echo "Le manifeste ne porte pas ${BON}Node,RBAC : le socle a changé, le lab ne s'applique plus." >&2
  exit 1
}
kubectl get --raw /readyz >/dev/null

install -d -m 0700 /var/lib/dsoxlab
cp -p "$MANIFESTE" "$COPIE"

# La faute. On exige trois silences consécutifs de l'API avant de conclure :
# un seul peut n'être que le redémarrage du conteneur.
sed -i "s|${BON}|${FAUX}|" "$MANIFESTE"
silences=0
for essai in $(seq 1 60); do
  if kubectl get --raw /readyz >/dev/null 2>&1; then
    silences=0
  else
    silences=$((silences + 1))
  fi
  if (( silences >= 3 )); then
    break
  fi
  sleep 3
done
if (( silences < 3 )); then
  echo "L'API répond encore après le changement de manifeste : le kubelet n'a pas redéployé le Pod." >&2
  exit 1
fi

echo "Situation posée : l'API server ne répond plus."
