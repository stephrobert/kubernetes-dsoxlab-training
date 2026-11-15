#!/usr/bin/env bash
# Pose deux pannes du plan de contrôle, en dernier, quand plus rien du setup
# n'a besoin de l'API :
#
#   1. les certificats apiserver et front-proxy-client réémis pour 20 jours :
#      kubeadm renouvelle avec la durée de la configuration qu'on lui passe
#      (certificateValidityPeriod), repris de k8s-challenge-sauvegarder-et-restaurer,
#      attesté le 2026-11-14. La ConfigMap kubeadm-config n'est PAS modifiée :
#      un renouvellement fait par l'apprenant reprend la durée normale ;
#   2. une lettre de trop sur le flag d'autorisation de l'API server, repris de
#      cka-troubleshoot-apiserver (attesté) : le kubelet redéploie le Pod
#      statique, l'API server refuse un flag inconnu et sort.
#
# Rejouable : le setup a d'abord rendu au manifeste son flag d'origine.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare-pannes.log) 2>&1
set -x

MANIFESTE=/etc/kubernetes/manifests/kube-apiserver.yaml
BON='--authorization-mode='
FAUX='--authorization-modes='

# 1. Les certificats à 20 jours.
CONFIG="$(mktemp)"
kubectl -n kube-system get configmap kubeadm-config -o jsonpath='{.data.ClusterConfiguration}' > "$CONFIG"
if grep -q '^certificateValidityPeriod:' "$CONFIG"; then
  sed -i 's/^certificateValidityPeriod:.*/certificateValidityPeriod: 480h0m0s/' "$CONFIG"
else
  echo "certificateValidityPeriod: 480h0m0s" >> "$CONFIG"
fi
kubeadm certs renew apiserver --config "$CONFIG"
kubeadm certs renew front-proxy-client --config "$CONFIG"
rm -f "$CONFIG"
openssl x509 -in /etc/kubernetes/pki/apiserver.crt -noout -enddate
openssl x509 -in /etc/kubernetes/pki/front-proxy-client.crt -noout -enddate

# 2. Le flag faux.
grep -q -- "${BON}Node,RBAC" "$MANIFESTE" || {
  echo "Le manifeste ne porte pas ${BON}Node,RBAC : le socle a changé, l'épreuve ne s'applique plus." >&2
  exit 1
}
sed -i "s|${BON}|${FAUX}|" "$MANIFESTE"

# Trois silences consécutifs de l'API avant de conclure : un seul peut n'être
# que le redémarrage du conteneur (cka-troubleshoot-apiserver).
silences=0
for _ in $(seq 1 60); do
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
echo "Pannes posées : deux certificats à 20 jours, l'API server ne répond plus."
