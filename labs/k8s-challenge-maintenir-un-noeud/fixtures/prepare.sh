#!/usr/bin/env bash
# Pose la situation du challenge, sur le cluster que setup.yaml vient de
# ramener en 1.36.4 :
#
#   - le namespace maintenance ;
#   - le dépôt git ~/maintenance de l'équipe, avec deux manifestes commités :
#     catalogue-config.yaml (MAX_CONNEXIONS=50) et catalogue.yaml ;
#   - ces deux manifestes appliqués TELS QUELS depuis le dépôt : un ConfigMap
#     et le Deployment catalogue, quatre exemplaires répartis sur les deux
#     nœuds par une contrainte de répartition, comme cka-node-drain-cordon ;
#   - un Pod sans contrôleur, outil-diag, sur le worker : le drain le refuse
#     par défaut ;
#   - l'heure de pose, notée en annotation du Deployment APRÈS que ses Pods
#     sont prêts : un Pod plus récent que cette heure a donc été recréé.
#
# Aucun budget, aucune trace : c'est le travail.
#
# Rejouable : le namespace est recréé, le dépôt aussi.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
DEPOT="${LAB_HOME}/maintenance"
WORKER=k8s-w1.lab

kubectl uncordon "$WORKER"
kubectl wait --for=condition=Ready "node/${WORKER}" --timeout=300s

if [[ "$(kubectl get namespace maintenance -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/maintenance --timeout=180s
fi
kubectl delete namespace maintenance --ignore-not-found --wait=true --timeout=180s
kubectl create namespace maintenance

rm -rf "$DEPOT"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "$DEPOT"

cat > "${DEPOT}/catalogue-config.yaml" <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: catalogue-config
  namespace: maintenance
data:
  MAX_CONNEXIONS: "50"
YAML

cat > "${DEPOT}/catalogue.yaml" <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: catalogue
  namespace: maintenance
spec:
  replicas: 4
  selector:
    matchLabels:
      app: catalogue
  template:
    metadata:
      labels:
        app: catalogue
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: catalogue
      containers:
        - name: web
          image: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
          ports:
            - containerPort: 80
          envFrom:
            - configMapRef:
                name: catalogue-config
          resources:
            requests:
              cpu: 50m
              memory: 32Mi
YAML

chown -R "$LAB_USER:$LAB_USER" "$DEPOT"
sudo -u "$LAB_USER" git -C "$DEPOT" init -q -b main
sudo -u "$LAB_USER" git -C "$DEPOT" config user.name "Équipe catalogue"
sudo -u "$LAB_USER" git -C "$DEPOT" config user.email "catalogue@boutique.lab"
sudo -u "$LAB_USER" git -C "$DEPOT" add catalogue-config.yaml catalogue.yaml
sudo -u "$LAB_USER" git -C "$DEPOT" commit -q -m "Manifestes du catalogue"

kubectl apply -f "${DEPOT}/catalogue-config.yaml" -f "${DEPOT}/catalogue.yaml"

kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: outil-diag
  namespace: maintenance
spec:
  nodeName: k8s-w1.lab
  containers:
    - name: shell
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "infinity"]
YAML

kubectl -n maintenance rollout status deployment/catalogue --timeout=300s
kubectl -n maintenance wait --for=condition=Ready pod/outil-diag --timeout=180s

# La situation exige des Pods du catalogue sur le worker : sinon il n'y a rien
# à évacuer.
SUR_W1="$(kubectl -n maintenance get pods -l app=catalogue -o json | python3 -c 'import json,sys; print(sum(1 for p in json.load(sys.stdin)["items"] if p["spec"].get("nodeName") == "k8s-w1.lab"))')"
if [[ "${SUR_W1}" -lt 1 ]]; then
  echo "Aucun Pod du catalogue sur k8s-w1.lab : la contrainte de répartition n'a pas joué." >&2
  exit 1
fi

# L'heure de pose vient APRÈS la naissance des Pods, à la seconde près : un Pod
# né dans la même seconde que la pose passerait sinon pour recréé.
sleep 2
kubectl -n maintenance annotate deployment catalogue --overwrite \
  "lab.dsoxlab/pose-le=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

kubectl get nodes -o wide
kubectl -n maintenance get pods -o wide
echo "Situation posée : cluster en 1.36, catalogue en 4/4 dont ${SUR_W1} sur ${WORKER}, outil-diag posé."
