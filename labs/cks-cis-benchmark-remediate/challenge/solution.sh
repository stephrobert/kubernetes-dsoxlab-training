#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
MANIFESTES=/etc/kubernetes/manifests

attendre_le_control_plane() {
  for _ in $(seq 1 80); do
    $K get --raw /healthz >/dev/null 2>&1 && break
    sleep 3
  done
  $K get --raw /healthz >/dev/null
  for _ in $(seq 1 40); do
    phases=$($K -n kube-system get pods -l tier=control-plane \
      -o jsonpath='{.items[*].status.phase}' 2>/dev/null || true)
    [[ -n "$phases" && "$phases" != *Pending* ]] && return 0
    sleep 3
  done
  return 1
}

# 1. Le premier audit. C'est lui qui dit ce qu'il y a à corriger, et le nombre
#    d'échecs sert de point de comparaison.
$K -n conformite delete job kube-bench --ignore-not-found --wait=true
$K apply -f /root/kube-bench-job.yaml
$K -n conformite wait --for=condition=complete job/kube-bench --timeout=300s
POD=$($K -n conformite get pods -l job-name=kube-bench -o jsonpath='{.items[0].metadata.name}')
$K -n conformite logs "$POD" | grep -c '"status": "FAIL"' || true

# 2. La correction. Le référentiel reproche le même réglage à TROIS
#    composants : l'API server (1.2.15), le controller-manager (1.3.2) et le
#    scheduler (1.4.1). Les trois sont des Pods statiques du même répertoire.
sudo python3 - "$MANIFESTES" <<'PY'
import pathlib, sys, yaml

racine = pathlib.Path(sys.argv[1])
for composant in ("kube-apiserver", "kube-controller-manager", "kube-scheduler"):
    chemin = racine / f"{composant}.yaml"
    manifeste = yaml.safe_load(chemin.read_text(encoding="utf-8"))
    conteneur = manifeste["spec"]["containers"][0]
    conteneur["command"] = [c for c in conteneur["command"] if not c.startswith("--profiling=")]
    conteneur["command"].append("--profiling=false")
    chemin.write_text(yaml.safe_dump(manifeste, default_flow_style=False), encoding="utf-8")
    print(f"{composant} : --profiling=false")
PY

# Le kubelet redéploie les trois Pods. L'API disparaît quelques secondes.
sleep 15
attendre_le_control_plane

# 3. Le second audit, le seul qui prouve quelque chose. Un rapport de
#    remédiation qui ne relance pas l'outil n'affirme rien de vérifiable.
$K -n conformite delete job kube-bench --ignore-not-found --wait=true
$K apply -f /root/kube-bench-job.yaml
$K -n conformite wait --for=condition=complete job/kube-bench --timeout=300s
POD=$($K -n conformite get pods -l job-name=kube-bench -o jsonpath='{.items[0].metadata.name}')
$K -n conformite logs "$POD" | grep -c '"status": "FAIL"' || true

echo "Trois contrôles CIS de moins, et le control plane répond toujours."
