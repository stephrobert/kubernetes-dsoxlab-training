#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NS=production

# 1. Le Pod corrigé. Les cinq défauts sont repris un par un : plus de
#    namespace de processus de l'hôte, plus de privilège, un utilisateur non
#    root, aucune escalade, toutes les capacités retirées, et une image
#    épinglée sur une version au lieu d'un tag flottant.
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
  namespace: production
  labels:
    app: secure-app
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
  containers:
    - name: app
      image: busybox:1.37
      command: ["sh", "-c", "sleep 86400"]
      securityContext:
        privileged: false
        allowPrivilegeEscalation: false
        capabilities:
          drop:
            - ALL
YAML
$K -n "$NS" wait --for=condition=ready pod/secure-app --timeout=180s

# 2. Le Pod fautif disparaît. Le corriger sans retirer l'ancien laisserait la
#    faille ouverte juste à côté du correctif, ce qui est le défaut le plus
#    fréquent d'une remédiation faite dans l'urgence.
$K -n "$NS" delete pod insecure-app --ignore-not-found --wait=true

# 3. La preuve, de l'intérieur. Le nombre de processus visibles est la mesure
#    la plus parlante : avec hostPID, le conteneur voyait ceux du nœud entier.
echo -n "identité du processus : "
$K -n "$NS" exec secure-app -- id -u
echo -n "processus visibles    : "
$K -n "$NS" exec secure-app -- sh -c 'ps -eo pid | wc -l'
echo "Sans hostPID, le conteneur ne voit que les siens."
