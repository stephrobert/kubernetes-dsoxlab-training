#!/usr/bin/env bash
# Pose la situation, dans cet ordre : le namespace et son ConfigMap sont
# créés, une sauvegarde « d'hier soir » est prise avec eux dedans, le
# namespace est supprimé, puis un objet est écrit APRÈS la sauvegarde. Ce
# dernier doit disparaître à la restauration : c'est ce qui distingue une
# vraie restauration d'un namespace recréé à la main. L'identité d'etcd et
# les UID d'origine sont notés pour les tests, hors de la base, puisque la
# base va être remplacée.
#
# Rejouable : remettre-etcd.sh a déjà ramené le cluster sur /var/lib/etcd ;
# ici tout ce que le lab a écrit est refait de zéro.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

ETAT_DIR=/var/lib/dsoxlab
ETAT="${ETAT_DIR}/cka-etcd-backup-restore.json"
SECOURS="${ETAT_DIR}/etcd-secours.db"
SAUVEGARDES=/opt/backup
PKI=/etc/kubernetes/pki/etcd
ETCDCTL="etcdctl --endpoints=https://127.0.0.1:2379 --cacert=${PKI}/ca.crt --cert=${PKI}/healthcheck-client.crt --key=${PKI}/healthcheck-client.key"

mkdir -p "${ETAT_DIR}"
chmod 700 "${ETAT_DIR}"
rm -rf "${SAUVEGARDES}" /var/lib/etcd-restored
mkdir -p "${SAUVEGARDES}"
rm -f "${ETAT}"

# Ce qu'un passage précédent a pu laisser.
if [[ "$(kubectl get namespace important-data -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/important-data --timeout=180s
fi
kubectl delete namespace important-data --ignore-not-found --wait=true --timeout=180s
kubectl -n default delete configmap bruit-apres-sauvegarde --ignore-not-found

# 1. Les données importantes.
kubectl create namespace important-data
kubectl -n important-data create configmap mission-critical --from-literal=status=healthy
kubectl -n important-data create secret generic db-credentials --from-literal=password=ne-pas-perdre
NS_UID="$(kubectl get namespace important-data -o jsonpath='{.metadata.uid}')"
CM_UID="$(kubectl -n important-data get configmap mission-critical -o jsonpath='{.metadata.uid}')"

# 2. La sauvegarde d'hier soir, avec ces données dedans.
${ETCDCTL} snapshot save "${SAUVEGARDES}/etcd-snapshot-previous.db"
etcdutl snapshot status "${SAUVEGARDES}/etcd-snapshot-previous.db" -w table
REV_PREV="$(etcdutl snapshot status "${SAUVEGARDES}/etcd-snapshot-previous.db" -w json | python3 -c 'import json,sys; print(json.load(sys.stdin)["revision"])')"

# 3. L'incident.
kubectl delete namespace important-data --wait=true --timeout=180s

# 4. Du bruit écrit après la sauvegarde : il doit disparaître à la restauration.
kubectl -n default create configmap bruit-apres-sauvegarde --from-literal=cree-le="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 5. L'identité d'etcd avant restauration, et la révision courante : la
#    sauvegarde fraîche du candidat doit être au moins à cette révision.
STATUT="$(${ETCDCTL} endpoint status -w json)"
MEMBER_ID="$(echo "${STATUT}" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["Status"]["header"]["member_id"])')"
CLUSTER_ID="$(echo "${STATUT}" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["Status"]["header"]["cluster_id"])')"
REVISION="$(echo "${STATUT}" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["Status"]["header"]["revision"])')"

# 6. L'instantané de secours du cleanup : l'état de départ du lab.
${ETCDCTL} snapshot save "${SECOURS}"

# Mesuré le 2026-09-15 : member_id et cluster_id ne changent PAS à la
# restauration quand --name, --initial-cluster et le jeton par défaut sont
# ceux du manifeste, etcd les calcule à partir des URL de pair. Ils sont
# notés pour mémoire ; la preuve de la restauration est la date de
# création du répertoire member, postérieure à cette pose.
cat > "${ETAT}" <<EOF
{"member_id": ${MEMBER_ID}, "cluster_id": ${CLUSTER_ID}, "revision": ${REVISION}, "revision_previous": ${REV_PREV},
 "ns_uid": "${NS_UID}", "cm_uid": "${CM_UID}", "date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)", "epoch": $(date +%s)}
EOF
chmod 600 "${ETAT}"
ls -la "${SAUVEGARDES}"
echo "important-data a disparu, la sauvegarde d'hier soir est dans ${SAUVEGARDES}, etcd member ${MEMBER_ID}, révision ${REVISION}."
