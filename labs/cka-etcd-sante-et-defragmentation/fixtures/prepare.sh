#!/usr/bin/env bash
# Gonfle la base etcd, puis la compacte : etcd garde un gros fichier presque
# vide, que seule une défragmentation réduira. Pose ensuite le fichier de
# réponses vide. La taille de la base après le gonflement est relevée dans
# /var/lib/dsoxlab/etcd-taille-avant : c'est la référence du test.
#
# Rejouable : le namespace de test est recréé.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
NOEUD="$(hostname)"
etcdctl() {
  kubectl -n kube-system exec "etcd-${NOEUD}" -- etcdctl \
    --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt \
    --key /etc/kubernetes/pki/etcd/server.key "$@"
}
set -x

kubectl delete namespace etcd-essai --ignore-not-found --wait=true --timeout=180s
kubectl create namespace etcd-essai
# 240 ConfigMaps de 512 Ko : environ 120 Mo écrits dans etcd.
head -c 524288 /dev/zero | tr '\000' x > /tmp/etcd-essai-donnee
set +x
for i in $(seq 1 240); do
  kubectl -n etcd-essai create configmap "lest-$i" --from-file=donnee=/tmp/etcd-essai-donnee > /dev/null
done
set -x
kubectl -n etcd-essai delete configmaps --all --wait=true > /dev/null
rm -f /tmp/etcd-essai-donnee

# Compacter jusqu'à la révision courante : la place devient libre DANS le
# fichier, sans que le fichier rapetisse.
revision=$(etcdctl endpoint status -w json | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["Status"]["header"]["revision"])')
etcdctl compact "$revision" --physical
etcdctl endpoint status -w json | python3 -c '
import json, sys
s = json.load(sys.stdin)[0]["Status"]
print("dbSize", s["dbSize"], "dbSizeInUse", s["dbSizeInUse"])
open("/var/lib/dsoxlab/etcd-taille-avant", "w").write(str(s["dbSize"]))
assert s["dbSize"] > 2 * s["dbSizeInUse"], "la base ne garde pas assez de place libre"
' 2>&1 || { mkdir -p /var/lib/dsoxlab; etcdctl endpoint status -w json | python3 -c 'import json,sys; s=json.load(sys.stdin)[0]["Status"]; open("/var/lib/dsoxlab/etcd-taille-avant","w").write(str(s["dbSize"])); assert s["dbSize"] > 2 * s["dbSizeInUse"]'; }

install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/etcd"
cat > "${LAB_HOME}/etcd/reponses.yaml" <<'YAML'
# Ce que vous lisez avec etcdctl. Remplacez chaque valeur vide.
#
# L'identifiant du membre etcd, en hexadécimal, tel que member list le donne.
member_id: ""
# Son point d'accès client (clientURLs).
endpoint: ""
# true si endpoint health le dit en bonne santé.
healthy: false
# Le quota d'espace de la base, en octets.
quota_bytes: 0
YAML
chown -R "$LAB_USER:$LAB_USER" "${LAB_HOME}/etcd"
echo "Lab posé : la base etcd garde de la place libre, ~/etcd/reponses.yaml attend ses réponses."
