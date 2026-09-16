#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NS=chaine

# 1. Récupérer le digest de l'image RÉELLEMENT exécutée.
#
#    Deux sources possibles, et on prend la plus directe. Kubernetes écrit
#    dans l'état de chaque Pod ce que le nœud a résolu, sous imageID : c'est
#    la vérité du runtime, pas une promesse du manifeste.
#
#    `crictl inspecti nginx:1.27-alpine` donnerait la même chose côté
#    containerd ; `docker inspect`, lui, n'existe pas sur ce nœud, et le lab
#    hérité de K8sExamLab le supposait installé.
IMAGE_ID=$($K -n "$NS" get pods -l app=pinned-app \
  -o jsonpath='{.items[0].status.containerStatuses[0].imageID}')
echo "imageID résolu par le nœud : ${IMAGE_ID}"

# L'imageID se présente sous la forme dépôt@sha256:<hex>. On ne garde que le
# digest, et on le recolle sur le nom court attendu dans le manifeste.
DIGEST="sha256:${IMAGE_ID##*sha256:}"
REFERENCE="nginx@${DIGEST}"
echo "référence immuable : ${REFERENCE}"

# 2. Épingler le Deployment. `set image` suffit et évite d'éditer le YAML à la
#    main, ce qui est le geste attendu à l'examen.
$K -n "$NS" set image deployment/pinned-app "web=${REFERENCE}"
$K -n "$NS" rollout status deployment/pinned-app --timeout=300s

# 3. La preuve : ce qui est déclaré et ce qui tourne sont le même digest.
DECLARE=$($K -n "$NS" get deployment pinned-app \
  -o jsonpath='{.spec.template.spec.containers[0].image}')
RESOLU=$($K -n "$NS" get pods -l app=pinned-app \
  -o jsonpath='{.items[0].status.containerStatuses[0].imageID}')
echo "déclaré : ${DECLARE}"
echo "résolu  : ${RESOLU}"
[[ "${DECLARE##*@}" == "${RESOLU##*@}" ]] && echo "les digests coïncident" || {
  echo "ÉCART entre le digest déclaré et le digest résolu"
  exit 1
}

$K -n "$NS" get deployment pinned-app -o wide
echo "pinned-app est épinglé sur le digest de l'image qu'il exécute, en deux exemplaires."
