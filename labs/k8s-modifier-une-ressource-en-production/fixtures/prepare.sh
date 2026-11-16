#!/usr/bin/env bash
# Pose la situation : le Deployment web du namespace magasin, deux conteneurs
# (web et log-agent), déployé depuis son manifeste « Git » ~/magasin/web.yaml de
# la session. Puis un opérateur le monte à quatre réplicas pendant un pic de
# charge, hors de Git : la dérive que l'apprenant devra résorber.
#
# L'uid du Deployment est noté en lieu sûr (root seul) : les tests vérifient que
# l'objet n'a pas été supprimé puis recréé (replace --force).
#
# Rejouable : le namespace, le manifeste et l'uid de référence sont refaits.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NS=magasin
SESSION="${SESSION_UTILISATEUR:?le setup passe le compte de la session}"
MAISON=$(getent passwd "$SESSION" | cut -d: -f6)
MANIFESTE="$MAISON/magasin/web.yaml"
REFERENCE=/var/lib/dsoxlab-lab/magasin-web.uid

if [[ "$(kubectl get namespace "$NS" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete "namespace/$NS" --timeout=180s
fi
kubectl delete namespace "$NS" --ignore-not-found --wait=true
kubectl create namespace "$NS"

install -d -o "$SESSION" -g "$SESSION" -m 0755 "$MAISON/magasin"
cat > "$MANIFESTE" <<'EOF'
# web.yaml : la version versionnée dans Git
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: magasin
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: web
          image: nginx:1.27@sha256:6784fb0834aa7dbbe12e3d7471e69c290df3e6ba810dc38b34ae33d3c1c05f7d
          ports:
            - containerPort: 80
        - name: log-agent
          image: busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e
          command: ["sh", "-c", "sleep 3600"]
EOF
chown "$SESSION:$SESSION" "$MANIFESTE"

kubectl apply -f "$MANIFESTE"
kubectl -n "$NS" rollout status deployment/web --timeout=180s

install -d -m 0700 /var/lib/dsoxlab-lab
kubectl -n "$NS" get deployment web -o jsonpath='{.metadata.uid}' > "$REFERENCE"
chmod 0600 "$REFERENCE"

# Le pic de charge : quatre réplicas, posés hors de Git.
kubectl -n "$NS" patch deployment web -p '{"spec":{"replicas":4}}'
kubectl -n "$NS" rollout status deployment/web --timeout=180s
kubectl -n "$NS" get pods -o wide

echo "Situation posée : web tourne à quatre réplicas, son manifeste en dit deux."
