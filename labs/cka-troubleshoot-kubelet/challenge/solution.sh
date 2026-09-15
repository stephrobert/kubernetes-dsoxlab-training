#!/usr/bin/env bash
# Solution du formateur. Rejouée sur le control plane après `dsoxlab run`,
# elle prouve que le lab est FAISABLE et que ses tests passent quand le
# travail est fait. Elle passe par `ssh k8s-w1.lab`, comme le candidat.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# Ce script est lu par `bash -s` depuis l'entrée standard : chaque ssh doit
# porter -n, sinon il avale le reste du script comme entrée. Mesuré le
# 2026-09-14 : sans -n, rien après le premier ssh ne s'exécutait, et le
# script rendait 0.

# 1. Le diagnostic : le nœud, puis le journal du kubelet sur le nœud, qui
#    nomme le champ refusé.
$K get nodes
ssh -n k8s-w1.lab 'systemctl is-active kubelet || true; sudo journalctl -u kubelet -n 30 --no-pager | grep -i -E "clusterDNS|invalid|error" | tail -3 || true'

# 2. La réparation : retirer la ligne ajoutée, garder le reste, relancer.
ssh -n k8s-w1.lab 'sudo grep -n -A3 "^clusterDNS:" /var/lib/kubelet/config.yaml; sudo sed -i "/999.999.999.999/d" /var/lib/kubelet/config.yaml; sudo systemctl restart kubelet; sleep 3; systemctl is-active kubelet'

# 3. La preuve : le nœud revient, et l'application avec lui.
$K wait --for=condition=Ready node/k8s-w1.lab --timeout=180s
$K -n production rollout status deployment/web-app --timeout=180s
$K -n production get pods -o wide
echo "k8s-w1.lab est Ready, sa configuration est saine, web-app est en 3/3."
