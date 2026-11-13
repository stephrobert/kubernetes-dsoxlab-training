#!/usr/bin/env bash
# Pose la situation du lab k8s-appliquer-une-recommandation-vpa :
#
#   - metrics-server v0.9.1, avec --kubelet-insecure-tls : sur kubeadm, le
#     kubelet sert des certificats auto-signés que metrics-server refuse sinon ;
#   - le VPA 1.8.1, par hack/vpa-up.sh (recommender, updater, contrôleur
#     d'admission) ;
#   - le Deployment catalogue, deux réplicas, avec des requests bien trop
#     basses et une limite CPU basse : c'est ce que la recommandation corrigera.
#     Aucun VPA : l'apprenant le crée.
#
# Rejouable : le namespace est attendu s'il se termine, puis recréé.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

MANIFESTE="${MANIFESTE:-/root/metrics-server-v0.9.1.yaml}"
VPA_DEPOT="${VPA_DEPOT:-/root/autoscaler-vpa-1.8.1}"
BUSYBOX="busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"

kubectl apply -f "${MANIFESTE}"
kubectl -n kube-system patch deployment metrics-server --type=json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
kubectl -n kube-system rollout status deployment/metrics-server --timeout=180s
for essai in $(seq 1 40); do
  kubectl top nodes >/dev/null 2>&1 && break
  sleep 5
done
kubectl top nodes

(cd "${VPA_DEPOT}/vertical-pod-autoscaler" && ./hack/vpa-up.sh)
for composant in vpa-recommender vpa-updater vpa-admission-controller; do
  kubectl -n kube-system rollout status "deployment/${composant}" --timeout=240s
done
kubectl wait --for=condition=Established crd/verticalpodautoscalers.autoscaling.k8s.io --timeout=60s

if [[ "$(kubectl get namespace dimensionnement -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/dimensionnement --timeout=180s
fi
kubectl get namespace dimensionnement >/dev/null 2>&1 || kubectl create namespace dimensionnement
kubectl -n dimensionnement delete verticalpodautoscalers --all --ignore-not-found
kubectl -n dimensionnement delete deployment catalogue --ignore-not-found --wait=true

# Le conteneur garde une soixantaine de Mo en mémoire et consomme un peu de CPU
# en continu : de quoi donner au recommender des mesures à lire.
cat <<YAML | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: catalogue
  namespace: dimensionnement
spec:
  replicas: 2
  selector:
    matchLabels:
      app: catalogue
  template:
    metadata:
      labels:
        app: catalogue
    spec:
      # La boucle sh ignore SIGTERM : sans ce délai court, l'ancien Pod reste
      # une trentaine de secondes en Terminating après chaque changement.
      terminationGracePeriodSeconds: 5
      containers:
        - name: catalogue
          image: ${BUSYBOX}
          command:
            - sh
            - -c
            - |
              tampon=\$(head -c 60000000 /dev/zero | tr '\000' a)
              while true; do
                i=0; while [ \$i -lt 3000 ]; do i=\$((i+1)); done
                sleep 1
              done
          resources:
            requests:
              cpu: 5m
              memory: 16Mi
            limits:
              cpu: 50m
              memory: 512Mi
YAML
kubectl -n dimensionnement rollout status deployment/catalogue --timeout=180s
echo "Lab posé : metrics-server et le VPA répondent, catalogue tourne avec des requests trop basses, sans VPA."
