#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

MANIFESTE=/etc/kubernetes/manifests/kube-apiserver.yaml
K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le diagnostic, sans API : le runtime voit le conteneur mort et garde ses
#    journaux, où l'API server dit lui-même quel flag il ne connaît pas.
sudo crictl ps -a --name kube-apiserver 2>/dev/null | head -3 || true
ID=$(sudo crictl ps -a --name kube-apiserver -q 2>/dev/null | head -1 || true)
if [[ -n "${ID}" ]]; then
  sudo crictl logs --tail 3 "${ID}" 2>&1 | tail -3 || true
fi
sudo grep -n -- '--authorization-mode' "$MANIFESTE"

# 2. La réparation : une lettre de trop, sans retirer la ligne.
sudo sed -i 's|--authorization-modes=|--authorization-mode=|' "$MANIFESTE"

# 3. La preuve : le kubelet redéploie le Pod statique, l'API répond.
for essai in $(seq 1 60); do
  if $K get --raw /healthz >/dev/null 2>&1; then
    break
  fi
  sleep 3
done
$K get --raw /healthz
echo
# Le Pod miroir ne passe « prêt » qu'après la sonde de readiness du kubelet,
# quelques secondes après que l'API répond : on attend l'état complet.
$K -n kube-system wait --for=condition=Ready pod/kube-apiserver-k8s-cp.lab --timeout=120s
$K get nodes
echo "L'API server répond, et son autorisation est toujours Node,RBAC."
