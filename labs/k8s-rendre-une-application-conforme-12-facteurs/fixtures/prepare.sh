#!/usr/bin/env bash
# Pose l'application FAUTIVE du namespace douze, celle que la leçon 12 facteurs
# montre en contre-exemple : configuration en dur dans les arguments, état sur
# un volume emptyDir du Pod, aucun preStop. Un Redis tourne à côté, ressource
# attachée que l'application n'utilise pas. Les manifestes de l'application
# attendent dans ~/douze, ceux du Redis restent hors de portée (/root).
#
# Rejouable : le namespace et ~/douze sont recréés.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NS=douze
SESSION="${SESSION_UTILISATEUR:?le setup passe le compte de la session}"
MAISON=$(getent passwd "$SESSION" | cut -d: -f6)
PODINFO='ghcr.io/stefanprodan/podinfo:6.17.0@sha256:fa2f27c1a8561097e5144bfc0853eba6054d743b68b03de4cad4675616ddefb0'
REDIS='redis:7.4.11-alpine@sha256:858f009f9709ce576febc734aa78b8f6d624b82571f9ddb6bda4377c833b3499'

if [[ "$(kubectl get namespace "$NS" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete "namespace/$NS" --timeout=180s
fi
kubectl delete namespace "$NS" --ignore-not-found --wait=true
kubectl create namespace "$NS"
rm -rf "$MAISON/douze"
install -d -o "$SESSION" -g "$SESSION" -m 0755 "$MAISON/douze"

# Le Redis : une ressource attachée, déjà là, que l'apprenant n'a pas à gérer.
cat > /root/douze-redis.yaml <<EOF
apiVersion: apps/v1
kind: Deployment
metadata: {name: redis, namespace: $NS}
spec:
  replicas: 1
  selector: {matchLabels: {app: redis}}
  template:
    metadata: {labels: {app: redis}}
    spec:
      containers:
      - name: redis
        image: $REDIS
        ports: [{name: redis, containerPort: 6379}]
        readinessProbe:
          exec: {command: ["redis-cli", "ping"]}
          periodSeconds: 2
---
apiVersion: v1
kind: Service
metadata: {name: redis, namespace: $NS}
spec:
  selector: {app: redis}
  ports: [{name: redis, port: 6379, targetPort: redis}]
EOF
kubectl apply -f /root/douze-redis.yaml

# L'application fautive, telle que l'équipe l'a livrée.
cat > "$MAISON/douze/deployment.yaml" <<EOF
# Livré tel quel par l'équipe : configuration en dur, état sur le disque du Pod.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: podinfo
spec:
  replicas: 2
  selector:
    matchLabels:
      app: podinfo
  template:
    metadata:
      labels:
        app: podinfo
    spec:
      terminationGracePeriodSeconds: 30
      containers:
        - name: podinfo
          image: $PODINFO
          command: ["./podinfo", "--ui-message=en dur dans args", "--data-path=/data"]
          ports:
            - name: http
              containerPort: 9898
          readinessProbe:
            httpGet: {path: /readyz, port: http}
            initialDelaySeconds: 1
            periodSeconds: 2
          volumeMounts:
            - name: data
              mountPath: /data
      volumes:
        - name: data
          emptyDir: {}
EOF
cat > "$MAISON/douze/service.yaml" <<EOF
apiVersion: v1
kind: Service
metadata:
  name: podinfo
spec:
  selector:
    app: podinfo
  ports:
    - name: http
      port: 80
      targetPort: http
EOF
chown "$SESSION:$SESSION" "$MAISON/douze/deployment.yaml" "$MAISON/douze/service.yaml"
kubectl -n "$NS" apply -f "$MAISON/douze/deployment.yaml" -f "$MAISON/douze/service.yaml"

kubectl -n "$NS" rollout status deploy/redis --timeout=180s
kubectl -n "$NS" rollout status deploy/podinfo --timeout=180s
kubectl -n "$NS" get pods -o wide

echo "Application fautive posée dans douze, manifestes dans $MAISON/douze."
