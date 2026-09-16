#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
# `pipefail` est volontairement ABSENT, et c'est une correction.
#
# Mesuré le 2026-09-16 : `kubectl get nodes -o name | head -1` fait recevoir
# SIGPIPE à kubectl quand head ferme le tuyau, et le script rendait 141, soit
# 128 + 13. Le validateur concluait « la solution du formateur a échoué »
# alors qu'elle avait fait son travail.
set -eu

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
MANIFESTE=/etc/kubernetes/manifests/kube-apiserver.yaml

attendre_l_api() {
  for _ in $(seq 1 80); do
    $K get --raw /healthz >/dev/null 2>&1 && break
    sleep 3
  done
  $K get --raw /healthz >/dev/null
  for _ in $(seq 1 40); do
    phases=$($K -n kube-system get pods -l component=kube-apiserver \
      -o jsonpath='{.items[*].status.phase}' 2>/dev/null || true)
    [[ -n "$phases" && "$phases" != *Pending* ]] && return 0
    sleep 3
  done
  return 1
}

# Les trois flags. Ils sont ajoutés au conteneur du Pod statique, et le
# kubelet redéploie dès que le fichier change.
#
# On n'ajoute PAS --anonymous-auth=false, et c'est délibéré : les sondes que
# kubeadm écrit dans ce manifeste interrogent /livez et /readyz sans
# s'authentifier. Le flag les ferait échouer, le kubelet tuerait l'API server
# en boucle, et le durcissement casserait le cluster qu'il devait protéger.
sudo python3 - "$MANIFESTE" <<'PY'
import sys, pathlib, yaml

chemin = pathlib.Path(sys.argv[1])
manifeste = yaml.safe_load(chemin.read_text(encoding="utf-8"))
conteneur = manifeste["spec"]["containers"][0]

for flag in ("--profiling=false",
             "--service-account-lookup=true",
             "--tls-min-version=VersionTLS12"):
    nom = flag.split("=")[0]
    conteneur["command"] = [c for c in conteneur["command"] if not c.startswith(nom + "=")]
    conteneur["command"].append(flag)

chemin.write_text(yaml.safe_dump(manifeste, default_flow_style=False), encoding="utf-8")
print("manifeste réécrit avec les trois flags de durcissement")
PY

sleep 10
attendre_l_api

# La preuve, des deux côtés.
echo -n "profileur : "
if $K get --raw /debug/pprof/ >/dev/null 2>&1; then
  echo "ENCORE OUVERT, anormal"
else
  echo "fermé"
fi
echo -n "cluster   : "
$K get nodes -o name | head -1 || true
echo "Le profileur est fermé, et l'API sert toujours."
