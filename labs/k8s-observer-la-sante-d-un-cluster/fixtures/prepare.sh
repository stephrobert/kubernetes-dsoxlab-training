#!/usr/bin/env bash
# Pose la situation : metrics-server n'est PAS installé, son manifeste épinglé
# (0.9.0, celui du lab cka-hpa-autoscaling) attend dans ~/sante de la session.
# Le namespace sante porte trois Pods, dont un, tiré au hasard, remplit 150 Mio
# de mémoire ; et un Deployment réserve 1200m de CPU sur k8s-w1.lab.
#
# Rejouable : metrics-server est retiré s'il traîne d'un passage précédent, le
# namespace est recréé, un nouveau Pod gourmand est tiré.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NS=sante
SESSION="${SESSION_UTILISATEUR:?le setup passe le compte de la session}"
MAISON=$(getent passwd "$SESSION" | cut -d: -f6)
MANIFESTE="${MANIFESTE:?le setup passe le manifeste de metrics-server}"
IMAGE='busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e'

# Ce que l'apprenant doit produire est retiré s'il traîne.
kubectl delete -f "$MANIFESTE" --ignore-not-found --wait=true

if [[ "$(kubectl get namespace "$NS" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete "namespace/$NS" --timeout=180s
fi
kubectl delete namespace "$NS" --ignore-not-found --wait=true
kubectl create namespace "$NS"

install -d -o "$SESSION" -g "$SESSION" -m 0755 "$MAISON/sante"
install -o "$SESSION" -g "$SESSION" -m 0644 "$MANIFESTE" "$MAISON/sante/metrics-server-v0.9.0.yaml"

# Trois Pods, un seul remplit 150 Mio d'un emptyDir en mémoire : ces pages
# comptent dans la mémoire de travail du conteneur, que kubectl top affiche.
pods=(api cache lot)
gourmand=${pods[$((RANDOM % 3))]}
for pod in "${pods[@]}"; do
  [[ "$pod" == "$gourmand" ]] && mio=150 || mio=4
  cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata: {name: $pod, namespace: $NS, labels: {app: $pod}}
spec:
  containers:
  - name: app
    image: $IMAGE
    command: ["sh", "-c", "dd if=/dev/zero of=/remplissage/bloc bs=1M count=$mio && sleep 36000"]
    resources:
      requests: {cpu: 10m, memory: 16Mi}
      limits: {memory: 256Mi}
    volumeMounts: [{name: remplissage, mountPath: /remplissage}]
  volumes:
  - name: remplissage
    emptyDir: {medium: Memory, sizeLimit: 200Mi}
EOF
done

# Une réservation de CPU sur k8s-w1.lab : des demandes, pas de la consommation.
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata: {name: reservation, namespace: $NS}
spec:
  replicas: 1
  selector: {matchLabels: {app: reservation}}
  template:
    metadata: {labels: {app: reservation}}
    spec:
      nodeSelector: {kubernetes.io/hostname: k8s-w1.lab}
      containers:
      - name: app
        image: $IMAGE
        command: ["sleep", "36000"]
        resources:
          requests: {cpu: 1200m, memory: 16Mi}
EOF

kubectl -n "$NS" wait --for=condition=Ready pod --all --timeout=180s
kubectl -n "$NS" get pods -o wide

echo "Situation posée : metrics-server absent, trois Pods à mesurer, une réservation de CPU sur k8s-w1.lab."
