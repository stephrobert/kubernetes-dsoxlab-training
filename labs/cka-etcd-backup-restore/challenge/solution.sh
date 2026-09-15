#!/usr/bin/env bash
# Solution du formateur. Rejouée sur le control plane après `dsoxlab run`,
# elle prouve que le lab est FAISABLE et que ses tests passent quand le
# travail est fait. Elle suit la procédure de l'examen : sauvegarder, arrêter
# etcd et l'API server en sortant leurs manifestes, restaurer dans un
# répertoire neuf, faire pointer le manifeste dessus, remettre les deux.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
PKI=/etc/kubernetes/pki/etcd
ETCDCTL="sudo etcdctl --endpoints=https://127.0.0.1:2379 --cacert=${PKI}/ca.crt --cert=${PKI}/healthcheck-client.crt --key=${PKI}/healthcheck-client.key"
MANIFESTES=/etc/kubernetes/manifests
HORS=/root/manifestes-hors-service

# 1. La sauvegarde fraîche, vérifiée. etcdctl parle au serveur, etcdutl lit
#    le fichier : `etcdctl snapshot status` n'existe plus et rendrait 0.
${ETCDCTL} snapshot save /opt/backup/etcd-snapshot.db
sudo etcdutl snapshot status /opt/backup/etcd-snapshot.db -w table

# 2. La sauvegarde d'hier soir est-elle lisible ?
sudo etcdutl snapshot status /opt/backup/etcd-snapshot-previous.db -w table

# 3. Arrêter etcd ET l'API server : sortir leurs manifestes du répertoire
#    surveillé. Arrêter le kubelet ne stopperait aucun des deux conteneurs.
sudo mkdir -p "${HORS}"
sudo mv "${MANIFESTES}/etcd.yaml" "${MANIFESTES}/kube-apiserver.yaml" "${HORS}/"
for essai in $(seq 1 45); do
  if [[ -z "$(sudo crictl ps --name etcd -q)" && -z "$(sudo crictl ps --name kube-apiserver -q)" ]]; then
    break
  fi
  sleep 2
done
sudo crictl ps --name etcd

# 4. Restaurer dans un répertoire neuf, sous l'identité que le manifeste
#    attend : nom du membre, cluster initial, URL de pair.
NOM="$(sudo sed -n 's/.*--name=//p' "${HORS}/etcd.yaml" | head -1)"
PAIRS="$(sudo sed -n 's/.*--initial-cluster=//p' "${HORS}/etcd.yaml" | head -1)"
ANNONCE="$(sudo sed -n 's/.*--initial-advertise-peer-urls=//p' "${HORS}/etcd.yaml" | head -1)"
sudo rm -rf /var/lib/etcd-restored
sudo etcdutl snapshot restore /opt/backup/etcd-snapshot-previous.db \
  --data-dir /var/lib/etcd-restored \
  --name "${NOM}" --initial-cluster "${PAIRS}" --initial-advertise-peer-urls "${ANNONCE}"

# 5. Le manifeste pointe sur le répertoire restauré : seul le hostPath
#    change, le conteneur continue de voir /var/lib/etcd. Le motif est ancré
#    sur « path: » en début de ligne : « mountPath: /var/lib/etcd » contient
#    la même chaîne, et le changer aussi ferait démarrer etcd à vide dans le
#    conteneur, sur un répertoire que rien ne monte.
sudo sed -i -E 's|^([[:space:]]*)path: /var/lib/etcd$|\1path: /var/lib/etcd-restored|' "${HORS}/etcd.yaml"
sudo grep -n -E '(mountPath|path): /var/lib/etcd' "${HORS}/etcd.yaml"
sudo mv "${HORS}/etcd.yaml" "${HORS}/kube-apiserver.yaml" "${MANIFESTES}/"

# 6. Le kubelet relance les deux ; l'API revient avec un cache neuf.
for essai in $(seq 1 90); do
  if $K get --raw /readyz >/dev/null 2>&1 && $K get node k8s-cp.lab >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
$K get nodes
${ETCDCTL} endpoint status -w table
$K get namespace important-data
$K -n important-data get configmap mission-critical -o jsonpath='{.data.status}{"\n"}'
echo "Le cluster tourne sur les données d'hier soir : important-data est revenu."
