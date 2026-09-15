#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# L'état de départ, mesuré dans le cgroup.
$K -n lab exec scaling-pod -- cat /sys/fs/cgroup/memory.max

# Le redimensionnement passe par la sous-ressource resize : kubectl edit
# refuserait, kubectl patch sait la viser. Patch stratégique, le défaut :
# un merge patch remplacerait toute la liste des conteneurs, image
# comprise, et l'API répondrait « only cpu and memory resources are
# mutable ». Mesuré le 2026-09-15.
$K -n lab patch pod scaling-pod --subresource resize \
  -p '{"spec":{"containers":[{"name":"app","resources":{"requests":{"cpu":"200m","memory":"64Mi"},"limits":{"cpu":"400m","memory":"256Mi"}}}]}}'

# Le kubelet applique en quelques secondes ; le statut dit quand c'est fait.
for essai in $(seq 1 30); do
  if [[ "$($K -n lab exec scaling-pod -- cat /sys/fs/cgroup/memory.max 2>/dev/null)" == "268435456" ]]; then
    break
  fi
  sleep 2
done

# La preuve : même Pod, zéro redémarrage, nouvelle limite dans le cgroup.
$K -n lab get pod scaling-pod -o jsonpath='{.metadata.creationTimestamp}{" "}{.metadata.annotations.lab\.dsoxlab/cree-le}{" restarts="}{.status.containerStatuses[0].restartCount}{"\n"}'
$K -n lab exec scaling-pod -- cat /sys/fs/cgroup/memory.max
echo "scaling-pod a été redimensionné en place."
