#!/usr/bin/env bash
# Solution du formateur. Rejouée sur le control plane après `dsoxlab run`,
# elle prouve que le lab est FAISABLE et que ses tests passent quand le
# travail est fait. Elle passe par `ssh k8s-w1.lab`, comme le candidat.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le diagnostic, depuis le control plane : quel nœud, depuis quand.
$K get nodes
$K describe node k8s-w1.lab | grep -A8 '^Conditions:' | head -10

# Ce script est lu par `bash -s` depuis l'entrée standard : chaque ssh doit
# porter -n, sinon il avale le reste du script comme entrée. Mesuré le
# 2026-09-14 : sans -n, rien après le premier ssh ne s'exécutait, et le
# script rendait 0.

# 2. Sur le nœud : le service est arrêté, et il est aussi désactivé.
ssh -n k8s-w1.lab 'systemctl is-active kubelet || true; systemctl is-enabled kubelet || true'

# 3. La réparation, durable : enable et start d'un coup.
ssh -n k8s-w1.lab 'sudo systemctl enable --now kubelet && systemctl is-enabled kubelet && systemctl is-active kubelet'

# 4. La preuve : le nœud revient, et l'application avec lui.
$K wait --for=condition=Ready node/k8s-w1.lab --timeout=180s
$K -n production rollout status deployment/web-app --timeout=180s
$K -n production get pods -o wide
echo "k8s-w1.lab est Ready, le kubelet est activé, web-app est en 3/3."
