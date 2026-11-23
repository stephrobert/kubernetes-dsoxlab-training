#!/usr/bin/env bash
# Pose la situation du lab k8s-chiffrer-les-secrets-au-repos sur k8s-cp.lab.
#
#   - l'API server tourne SANS chiffrement au repos : les Secrets sont ecrits
#     en clair dans etcd (etat kubeadm d'origine) ;
#   - le namespace tresorerie porte deux Secrets, cle-banque et cle-paie,
#     donc deja ecrits en clair ;
#   - le ServiceAccount facturation y lit TOUS les Secrets (get, list, watch),
#     alors qu'il n'a besoin que de cle-banque.
#
# Precaution reprise de cks-restreindre-l-acces-anonyme : la sauvegarde du
# manifeste vit dans /var/backups, JAMAIS dans /etc/kubernetes/manifests, que
# le kubelet surveille.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

MANIFESTE=/etc/kubernetes/manifests/kube-apiserver.yaml
SAUVEGARDE=/var/backups/kube-apiserver.avant-chiffrement.yaml
# Depose par setup.yaml : ansible.builtin.script ne copie que le script appele.
DECHIFFRER=/var/lib/dsoxlab/dechiffrer-secrets.sh

# 1. Un passage precedent a pu laisser l'API server chiffrer : on dechiffre
#    tout avant de repartir de l'etat d'origine.
bash "$DECHIFFRER"

# 2. La sauvegarde de l'etat d'origine, prise une seule fois.
[[ -f "$SAUVEGARDE" ]] || cp -f "$MANIFESTE" "$SAUVEGARDE"
if grep -q -- '--encryption-provider-config' "$SAUVEGARDE"; then
  echo "La sauvegarde du manifeste chiffre deja : le socle a change." >&2
  exit 1
fi

# 3. Le namespace et ses Secrets, ecrits en clair.
if [[ "$(kubectl get namespace tresorerie -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/tresorerie --timeout=180s
fi
kubectl delete namespace tresorerie --ignore-not-found --wait=true --timeout=180s
kubectl create namespace tresorerie
kubectl -n tresorerie create secret generic cle-banque --from-literal=iban=FR7630006000011234567890189
kubectl -n tresorerie create secret generic cle-paie --from-literal=jeton=Paie-Kappa-2026
kubectl -n tresorerie create serviceaccount facturation
kubectl -n tresorerie create role lecture-secrets --verb=get,list,watch --resource=secrets
kubectl -n tresorerie create rolebinding facturation-secrets \
  --role=lecture-secrets --serviceaccount=tresorerie:facturation

# 4. On montre l'etat de depart dans le journal : la valeur est lisible dans etcd.
etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  get /registry/secrets/tresorerie/cle-paie --print-value-only | grep -a -q Paie-Kappa-2026
echo "Situation posee : Secrets en clair dans etcd, facturation lit tout."
