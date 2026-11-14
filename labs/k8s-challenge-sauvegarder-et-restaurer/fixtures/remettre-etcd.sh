#!/usr/bin/env bash
# Ramène le cluster sur /var/lib/etcd avec le manifeste d'origine, sans
# perdre les données courantes. Joué par le setup, pour repartir propre, et
# par le cleanup, pour ne pas laisser le cluster sur un répertoire restauré
# que le lab suivant ne connaît pas.
#
# Trois cas, dans l'ordre où ils sont tentés :
#   1. etcd tourne déjà sur /var/lib/etcd et le cluster est sain : rien.
#   2. etcd tourne ailleurs, ou un manifeste manque : on arrête etcd et
#      l'API server en sortant leurs manifestes, on déplace les données
#      courantes vers /var/lib/etcd, on remet les manifestes d'origine.
#   3. Le cluster ne revient pas : on restaure l'instantané de secours pris
#      par le setup, l'état de départ du lab.
#
# Arrêter le kubelet n'arrêterait pas etcd, mesuré le 2026-09-15 : c'est le
# manifeste qu'on sort, et on attend que crictl ne voie plus le conteneur.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-remettre-etcd.log) 2>&1
set -x

MANIFESTES=/etc/kubernetes/manifests
M="${MANIFESTES}/etcd.yaml"
A="${MANIFESTES}/kube-apiserver.yaml"
ETAT=/var/lib/dsoxlab
ORIGINE="${ETAT}/etcd.yaml.origine"
SECOURS="${ETAT}/etcd-secours.db"
HORS=/root/dsoxlab-manifestes-hors-service
K="kubectl --kubeconfig /etc/kubernetes/admin.conf"

mkdir -p "${ETAT}" "${HORS}"
chmod 700 "${ETAT}"

hostpath_courant() {
  # Le hostPath du volume etcd-data, lu dans le YAML : un grep sur « path: »
  # attraperait aussi le path de la sonde livez, mesuré le 2026-09-15.
  [[ -f "$1" ]] || return 1
  python3 - "$1" <<'PY'
import sys
import yaml
doc = yaml.safe_load(open(sys.argv[1])) or {}
volumes = (doc.get("spec") or {}).get("volumes") or []
candidats = [v for v in volumes if v.get("name") == "etcd-data"] or [
    v for v in volumes if "pki" not in ((v.get("hostPath") or {}).get("path") or "")
]
for v in candidats:
    chemin = (v.get("hostPath") or {}).get("path")
    if chemin:
        print(chemin)
        break
PY
}

sain() {
  $K get --raw /readyz >/dev/null 2>&1 && $K get node k8s-cp.lab >/dev/null 2>&1
}

attendre_sain() {
  for essai in $(seq 1 90); do
    if sain; then return 0; fi
    sleep 2
  done
  return 1
}

attendre_arret() {
  for essai in $(seq 1 45); do
    if [[ -z "$(crictl ps --name "$1" -q 2>/dev/null)" ]]; then return 0; fi
    sleep 2
  done
  echo "Le conteneur $1 tourne encore après 90 s." >&2
  return 1
}

sortir_les_manifestes() {
  [[ -f "$M" ]] && mv -f "$M" "${HORS}/etcd.yaml"
  [[ -f "$A" ]] && mv -f "$A" "${HORS}/kube-apiserver.yaml"
  attendre_arret etcd
  attendre_arret kube-apiserver
}

remettre_les_manifestes() {
  cp -f "${ORIGINE}" "$M"
  if [[ -f "${HORS}/kube-apiserver.yaml" ]]; then
    mv -f "${HORS}/kube-apiserver.yaml" "$A"
  fi
}

# Le manifeste d'origine est conservé au premier passage, quand etcd tourne
# encore sur /var/lib/etcd, celui que kubeadm a écrit.
if [[ ! -f "${ORIGINE}" ]]; then
  if [[ -f "$M" && "$(hostpath_courant "$M")" == "/var/lib/etcd" ]]; then
    cp -f "$M" "${ORIGINE}"
  else
    echo "Pas de manifeste d'origine conservé et etcd n'est pas sur /var/lib/etcd." >&2
    exit 1
  fi
fi

COURANT="$(hostpath_courant "$M" || true)"
if [[ -f "$M" && -f "$A" && "${COURANT}" == "/var/lib/etcd" ]] && attendre_sain; then
  rm -rf /var/lib/etcd-restored
  echo "etcd tourne sur /var/lib/etcd et le cluster est sain : rien à faire."
  exit 0
fi

# Cas 2 : arrêter, déplacer les données courantes, remettre les manifestes.
sortir_les_manifestes
DONNEES=false
if [[ -n "${COURANT}" && "${COURANT}" != "/var/lib/etcd" && -d "${COURANT}/member" ]]; then
  rm -rf /var/lib/etcd
  mv "${COURANT}" /var/lib/etcd
  DONNEES=true
elif [[ -d /var/lib/etcd/member ]]; then
  DONNEES=true
fi
remettre_les_manifestes
if [[ "${DONNEES}" == true ]] && attendre_sain; then
  rm -rf /var/lib/etcd-restored
  echo "etcd ramené sur /var/lib/etcd avec ses données courantes."
  exit 0
fi

# Cas 3 : l'état de départ du lab, depuis l'instantané de secours.
if [[ ! -f "${SECOURS}" ]]; then
  echo "Le cluster ne revient pas et il n'y a pas d'instantané de secours." >&2
  exit 1
fi
sortir_les_manifestes
rm -rf /var/lib/etcd /var/lib/etcd-restored
NOM="$(sed -n 's/.*--name=//p' "${ORIGINE}" | head -1)"
PAIRS="$(sed -n 's/.*--initial-cluster=//p' "${ORIGINE}" | head -1)"
ANNONCE="$(sed -n 's/.*--initial-advertise-peer-urls=//p' "${ORIGINE}" | head -1)"
etcdutl snapshot restore "${SECOURS}" --data-dir /var/lib/etcd \
  --name "${NOM}" --initial-cluster "${PAIRS}" --initial-advertise-peer-urls "${ANNONCE}"
remettre_les_manifestes
attendre_sain
echo "etcd restauré depuis l'instantané de secours, l'état de départ du lab."
