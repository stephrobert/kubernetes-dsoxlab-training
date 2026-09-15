#!/usr/bin/env bash
# Solution du formateur. Rejouée sur le control plane après `dsoxlab run`,
# elle prouve que le lab est FAISABLE et que ses tests passent quand le
# travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le diagnostic : le Pod sans image, et l'historique.
$K -n lab get pods -l app=webapp
$K -n lab rollout history deployment/webapp

# 2. Défaire le déploiement bloqué : retour à la révision précédente. Le
#    ReplicaSet de la 1.26 est réactivé et prend le numéro 3.
$K -n lab rollout undo deployment/webapp
$K -n lab rollout status deployment/webapp --timeout=180s

# 3. Livrer la bonne image, avec la cause du changement : révision 4.
$K -n lab set image deployment/webapp nginx=nginx:1.27-alpine
$K -n lab annotate deployment/webapp kubernetes.io/change-cause="image corrigee : nginx:1.27-alpine" --overwrite
$K -n lab rollout status deployment/webapp --timeout=180s

# 4. L'historique raconte l'opération, et le ReplicaSet fautif est à zéro.
$K -n lab rollout history deployment/webapp
$K -n lab get rs -l app=webapp -o custom-columns='NOM:.metadata.name,REVISION:.metadata.annotations.deployment\.kubernetes\.io/revision,IMAGE:.spec.template.spec.containers[0].image,REPLICAS:.spec.replicas'
echo "webapp est en 1.27-alpine, trois replicas, après un retour arrière propre."
