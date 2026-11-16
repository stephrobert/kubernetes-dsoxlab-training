#!/usr/bin/env bash
# Pose la situation : quatre applications du namespace placement restent en
# Pending, chacune pour une cause de la leçon « Diagnostiquer un Pod Pending » :
#   calcul   demande 100 CPU (Insufficient cpu) ;
#   cache    exige disk=ssd-nvme, qu'aucun nœud ne porte ;
#   batch    est réservée à k8s-w1.lab, qui porte la taint equipe=batch:NoSchedule
#            qu'elle ne tolère pas ;
#   archives monte le PVC archives-data, de classe « lente », qu'aucun volume ne lie.
#
# Rejouable : la taint et l'étiquette sont reposées ou retirées, les PV de la
# classe « lente » laissés par un passage précédent sont supprimés.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NS=placement
IMAGE='nginx:1.27@sha256:6784fb0834aa7dbbe12e3d7471e69c290df3e6ba810dc38b34ae33d3c1c05f7d'

if [[ "$(kubectl get namespace "$NS" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete "namespace/$NS" --timeout=180s
fi
kubectl delete namespace "$NS" --ignore-not-found --wait=true
kubectl create namespace "$NS"

# Les PV de la classe « lente » d'un passage précédent : sans les retirer, le
# PVC du nouveau passage se lierait tout seul et le Pod démarrerait.
for pv in $(kubectl get pv -o jsonpath='{range .items[?(@.spec.storageClassName=="lente")]}{.metadata.name}{" "}{end}'); do
  kubectl delete pv "$pv" --wait=true
done

# La réserve de l'équipe batch, et aucun nœud étiqueté NVMe.
kubectl taint nodes k8s-w1.lab equipe=batch:NoSchedule --overwrite
kubectl label nodes --all disk- || true

cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata: {name: calcul, namespace: $NS}
spec:
  replicas: 1
  selector: {matchLabels: {app: calcul}}
  template:
    metadata: {labels: {app: calcul}}
    spec:
      containers:
      - name: app
        image: $IMAGE
        resources:
          requests: {cpu: "100", memory: 64Mi}
---
apiVersion: apps/v1
kind: Deployment
metadata: {name: cache, namespace: $NS}
spec:
  replicas: 1
  selector: {matchLabels: {app: cache}}
  template:
    metadata: {labels: {app: cache}}
    spec:
      nodeSelector: {disk: ssd-nvme}
      containers:
      - name: app
        image: $IMAGE
---
apiVersion: apps/v1
kind: Deployment
metadata: {name: batch, namespace: $NS}
spec:
  replicas: 1
  selector: {matchLabels: {app: batch}}
  template:
    metadata: {labels: {app: batch}}
    spec:
      nodeSelector: {kubernetes.io/hostname: k8s-w1.lab}
      containers:
      - name: app
        image: $IMAGE
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata: {name: archives-data, namespace: $NS}
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: lente
  resources:
    requests: {storage: 1Gi}
---
apiVersion: apps/v1
kind: Deployment
metadata: {name: archives, namespace: $NS}
spec:
  replicas: 1
  selector: {matchLabels: {app: archives}}
  template:
    metadata: {labels: {app: archives}}
    spec:
      containers:
      - name: app
        image: $IMAGE
        volumeMounts: [{name: data, mountPath: /data}]
      volumes:
      - name: data
        persistentVolumeClaim: {claimName: archives-data}
EOF

# On attend que les quatre Pods portent leur FailedScheduling : c'est ce que
# l'apprenant doit lire en arrivant.
for essai in $(seq 1 40); do
  bloques=$(kubectl -n "$NS" get events --field-selector reason=FailedScheduling \
    -o jsonpath='{range .items[*]}{.involvedObject.name}{"\n"}{end}' | sed 's/-[a-z0-9]*-[a-z0-9]*$//' | sort -u | wc -l)
  [[ "$bloques" -ge 4 ]] && break
  sleep 3
done
kubectl -n "$NS" get pods -o wide

echo "Situation posée : calcul, cache, batch et archives restent en Pending."
