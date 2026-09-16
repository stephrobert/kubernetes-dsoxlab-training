#!/usr/bin/env bash
# Pose la situation : un noeud dont containerd connait DEUX runtimes, et un
# namespace vide.
#
# Le runtime est installe par le setup, pas par le candidat : installer gVisor
# n'est pas la competence que l'examen mesure, et cela prendrait la moitie du
# temps du lab. Ce qui est demande au candidat, c'est de s'en servir.
#
# TROIS PIEGES DE DISTRIBUTION, mesures le 2026-09-16 :
#
#   1. gVisor ne publie plus ses binaires separement. L'URL
#      .../latest/x86_64/containerd-shim-runsc-v1 rend 404, et seule l'archive
#      gvisor.tar.bz2 porte encore le shim.
#   2. bzip2 n'est pas installe sur une Ubuntu 24.04 minimale : tar echoue avec
#      « bzip2: Cannot exec ».
#   3. Le paquet APT `runsc` d'Ubuntu date de 2023 et ne fournit pas le shim.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

CONF=/etc/containerd/config.toml
SAUVEGARDE=/var/backups/containerd.avant-gvisor.toml
mkdir -p /var/backups

attendre_l_api() {
  for _ in $(seq 1 60); do
    kubectl get --raw /healthz >/dev/null 2>&1 && return 0
    sleep 3
  done
  echo "L API server ne repond plus apres le redemarrage de containerd." >&2
  return 1
}

if [[ ! -f "$SAUVEGARDE" ]]; then
  cp -f "$CONF" "$SAUVEGARDE"
fi

if ! command -v runsc >/dev/null 2>&1 || [[ ! -x /usr/local/bin/containerd-shim-runsc-v1 ]]; then
  command -v bzip2 >/dev/null 2>&1 || { apt-get update -qq; apt-get install -y -qq bzip2; }
  cd /tmp
  curl -fsSL -o gvisor.tar.bz2 \
    "https://storage.googleapis.com/gvisor/releases/release/latest/x86_64/gvisor.tar.bz2"
  tar xjf gvisor.tar.bz2
  install -m 0755 runsc /usr/local/bin/runsc
  install -m 0755 containerd-shim-runsc-v1 /usr/local/bin/containerd-shim-runsc-v1
  rm -f gvisor.tar.bz2
fi
runsc --version | head -1

if ! grep -q "runtimes.runsc" "$CONF"; then
  cat >> "$CONF" <<'TOML'

[plugins."io.containerd.cri.v1.runtime".containerd.runtimes.runsc]
  runtime_type = "io.containerd.runsc.v1"
TOML
  systemctl restart containerd
  sleep 10
fi
systemctl is-active containerd
attendre_l_api

# Ce que le candidat doit produire est retire s'il traine d'un passage
# precedent : la RuntimeClass est un objet de CLUSTER et survivrait au
# namespace.
kubectl delete runtimeclass gvisor --ignore-not-found --wait=true

if [[ "$(kubectl get namespace bac-a-sable -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/bac-a-sable --timeout=180s
fi
kubectl get namespace bac-a-sable >/dev/null 2>&1 || kubectl create namespace bac-a-sable
kubectl -n bac-a-sable delete pod confine ordinaire --ignore-not-found --wait=true

# Le Pod temoin, lance par le runtime PAR DEFAUT. Il sert de point de
# comparaison : sans lui, on ne saurait pas distinguer « le bac a sable isole »
# de « tous les Pods voient ce noyau ».
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: ordinaire
  namespace: bac-a-sable
spec:
  nodeName: k8s-cp.lab
  containers:
    - name: outil
      image: busybox:1.37
      command: ["sh", "-c", "sleep 86400"]
YAML
kubectl -n bac-a-sable wait --for=condition=ready pod/ordinaire --timeout=180s

echo "Situation posee : containerd connait runsc, et aucune RuntimeClass ne le declare."
