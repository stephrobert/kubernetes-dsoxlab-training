#!/usr/bin/env bash
# Pose la situation du challenge : le dépôt git ~/annuaire (une ConfigMap,
# un Deployment à deux réplicas, un Service), appliqué tel quel, puis trois
# modifications faites en direct sur le cluster, comme une astreinte de nuit :
#
#   - la montée à N réplicas, N tiré entre 3 et 5 : c'est la seule que
#     l'équipe garde, elle doit finir dans le dépôt ;
#   - CACHE_TTL changé dans la ConfigMap : à défaire ;
#   - une variable DEBUG ajoutée au conteneur par `kubectl set env` : à
#     défaire. Elle n'est pas dans la dernière configuration appliquée,
#     donc `kubectl diff` ne la montre pas et `kubectl apply` ne la retire
#     pas.
#
# La mémoire garde N, la valeur du dépôt, le commit initial et les UID des
# objets : les tests exigent qu'ils n'aient pas été recréés.
# Rejouable : le namespace et le dépôt sont recréés à neuf.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NS=annuaire
LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
DEPOT="${LAB_HOME}/annuaire"
MEMOIRE=/var/lib/dsoxlab/challenge-ramener-le-cluster-au-depot.json
NGINX="nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
TTL_DEPOT=300

if [[ "$(kubectl get namespace "$NS" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete "namespace/$NS" --timeout=180s
fi
kubectl delete namespace "$NS" --ignore-not-found --wait=true --timeout=180s
kubectl create namespace "$NS"
rm -rf "$DEPOT"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "$DEPOT"

cat > "${DEPOT}/configmap.yaml" <<YAML
apiVersion: v1
kind: ConfigMap
metadata:
  name: annuaire-config
  namespace: ${NS}
data:
  CACHE_TTL: "${TTL_DEPOT}"
  ANNUAIRE_REGION: "ouest"
YAML

cat > "${DEPOT}/deployment.yaml" <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: annuaire-api
  namespace: ${NS}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: annuaire-api
  template:
    metadata:
      labels:
        app: annuaire-api
    spec:
      containers:
        - name: api
          image: ${NGINX}
          ports:
            - containerPort: 80
          envFrom:
            - configMapRef:
                name: annuaire-config
YAML

cat > "${DEPOT}/service.yaml" <<YAML
apiVersion: v1
kind: Service
metadata:
  name: annuaire-api
  namespace: ${NS}
spec:
  selector:
    app: annuaire-api
  ports:
    - port: 80
      targetPort: 80
YAML

chown -R "$LAB_USER:$LAB_USER" "$DEPOT"
sudo -u "$LAB_USER" git -C "$DEPOT" init -q -b main
sudo -u "$LAB_USER" git -C "$DEPOT" config user.name "Équipe annuaire"
sudo -u "$LAB_USER" git -C "$DEPOT" config user.email "annuaire@entreprise.lab"
sudo -u "$LAB_USER" git -C "$DEPOT" add configmap.yaml deployment.yaml service.yaml
sudo -u "$LAB_USER" git -C "$DEPOT" commit -q -m "Manifestes de l'annuaire"
COMMIT=$(sudo -u "$LAB_USER" git -C "$DEPOT" rev-parse HEAD)

kubectl apply -f "$DEPOT"
kubectl rollout status deployment/annuaire-api -n "$NS" --timeout=180s

# L'astreinte de nuit, en direct sur le cluster.
REPLICAS=$(( 3 + RANDOM % 3 ))
TTL_DIRECT=$(( 5 + RANDOM % 50 ))
kubectl scale deployment annuaire-api -n "$NS" --replicas="$REPLICAS"
kubectl patch configmap annuaire-config -n "$NS" --type merge -p "{\"data\":{\"CACHE_TTL\":\"${TTL_DIRECT}\"}}"
kubectl set env deployment/annuaire-api -n "$NS" DEBUG=1
kubectl rollout status deployment/annuaire-api -n "$NS" --timeout=180s

UID_DEP=$(kubectl get deployment annuaire-api -n "$NS" -o jsonpath='{.metadata.uid}')
UID_CM=$(kubectl get configmap annuaire-config -n "$NS" -o jsonpath='{.metadata.uid}')

install -d -m 0755 /var/lib/dsoxlab
printf '{"replicas": %d, "ttl_depot": "%s", "commit": "%s", "uid_deployment": "%s", "uid_configmap": "%s"}\n' \
  "$REPLICAS" "$TTL_DEPOT" "$COMMIT" "$UID_DEP" "$UID_CM" > "$MEMOIRE"
chmod 0600 "$MEMOIRE"

kubectl get all,configmaps -n "$NS"
echo "Situation posée : ~/annuaire au commit initial, trois modifications faites en direct."
