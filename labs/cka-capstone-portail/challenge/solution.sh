#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le capstone est FAISABLE et que ses huit tests passent quand le travail
# est fait.
#
# C'est UNE solution, pas LA solution. Le défaut de stockage se corrige aussi
# bien en créant un volume qui satisfait la réclamation qu'en réécrivant la
# réclamation pour une classe qui existe ; le défaut de sélecteur se corrige
# côté Service ou côté labels des Pods. Les tests mesurent le RÉSULTAT, pas le
# chemin.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NS=production

# ----------------------------------------------------------------------
# Défaut 1 : le portail réserve 4 CPU par exemplaire, les nœuds en ont 2.
# Les events du Pod disent « Insufficient cpu ». On redescend à une réserve
# réaliste ; nginx au repos consomme quelques millicores.
# ----------------------------------------------------------------------
$K -n "$NS" set resources deployment/portail --requests=cpu=100m,memory=64Mi
$K -n "$NS" rollout status deployment/portail --timeout=180s

# ----------------------------------------------------------------------
# Défaut 2 : la réclamation portail-data cherche la classe « rapide », que
# rien ne fournit. On lui donne un volume qui correspond, sur le disque des
# nœuds. Les trois critères d'appariement sont la classe, la taille et le
# mode d'accès : un seul qui diffère, et la réclamation reste en attente.
# ----------------------------------------------------------------------
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: portail-pv
spec:
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  storageClassName: rapide
  persistentVolumeReclaimPolicy: Delete
  hostPath:
    path: /mnt/portail-data
YAML
$K -n "$NS" wait --for=jsonpath='{.status.phase}'=Bound pvc/portail-data --timeout=120s
$K -n "$NS" rollout status deployment/archives --timeout=180s

# ----------------------------------------------------------------------
# Défaut 3 et exigence 3 : le Service sélectionne app=portal, les Pods portent
# app=portail. On corrige le sélecteur, et on l'expose sur le port 30080 de
# chaque nœud, ce que l'équipe n'avait jamais fait.
# ----------------------------------------------------------------------
$K -n "$NS" patch service portail-svc --type=merge -p \
  '{"spec":{"type":"NodePort","selector":{"app":"portail"},"ports":[{"name":"http","protocol":"TCP","port":80,"targetPort":80,"nodePort":30080}]}}'

# Un Service correct n'est pas encore un port ouvert. L'objet est à jour dans
# l'API dès le patch, mais c'est kube-proxy qui programme la règle iptables du
# NodePort sur chaque nœud, et il le fait APRÈS avoir été notifié.
#
# Mesuré le 2026-09-15 sur ce cluster : la chaîne KUBE-NODEPORTS est encore
# vide dans la seconde qui suit le patch, puis la règle apparaît en 1048 ms au
# premier passage, et en une douzaine de millisecondes ensuite. Une version
# antérieure de cette solution interrogeait le port immédiatement, recevait
# « Failed to connect », et rendait le capstone ROUGE alors que le travail
# était juste. On attend donc le port, pas l'objet.
for _ in $(seq 1 30); do
  curl -sS -o /dev/null -m 2 "http://127.0.0.1:30080/" 2>/dev/null && break
  sleep 1
done

# ----------------------------------------------------------------------
# La preuve, défaut par défaut.
# ----------------------------------------------------------------------
$K -n "$NS" get pods -o wide
echo -n "endpoints du service : "
$K -n "$NS" get endpointslice -l kubernetes.io/service-name=portail-svc \
  -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]}{" "}{end}'; echo

POD_ARCHIVES=$($K -n "$NS" get pods -l app=archives -o jsonpath='{.items[0].metadata.name}')
$K -n "$NS" exec "$POD_ARCHIVES" -- sh -c 'echo preuve > /data/preuve.txt && cat /data/preuve.txt'

# Le portail répond depuis CHAQUE nœud : c'est la propriété d'un NodePort, et
# c'est ce que la supervision vérifiera.
for ip in $($K get nodes -o jsonpath='{range .items[*]}{.status.addresses[?(@.type=="InternalIP")].address}{"\n"}{end}'); do
  echo -n "portail sur ${ip}:30080 : "
  curl -sS -o /dev/null -w '%{http_code}\n' -m 5 "http://${ip}:30080/"
done
echo "Le portail est en deux exemplaires, joignable sur chaque nœud, et les archives écrivent."
