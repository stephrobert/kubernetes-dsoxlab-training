#!/usr/bin/env bash
# Pose la situation du challenge k8s-challenge-livrer-avec-helm-et-gitops sur
# k8s-kind.lab, après le socle kind et Argo CD :
#
#   - un registre d'images sans authentification dans le namespace registre,
#     servi en NodePort 30500. containerd le tire en localhost:30500 sans
#     configuration du nœud (mesuré le 2026-11-11 pour k8s-gerer-les-images) ;
#     depuis la VM, docker y pousse par un port-forward ;
#   - ~/livraison/app : le contexte de build de l'application vitrine. Sa page
#     porte un JETON tiré au sort, mémorisé dans /var/lib/dsoxlab : il prouve
#     que l'image qui tourne vient bien de ce contexte ;
#   - ~/livraison/chart-vitrine : un chart Helm local, à installer avec un
#     fichier de values ;
#   - un dépôt Git nu, /srv/git/catalogue.git, servi en SSH par le compte git
#     (git-shell) sur l'adresse que le réseau kind voit de la VM, 172.18.0.1 ;
#     un clone de travail en ~/livraison/catalogue ;
#   - les accès d'Argo CD à ce dépôt : un Secret de dépôt (clé SSH dédiée) ;
#     la clé d'hôte de la VM vient du setup. L'Application, elle, est le
#     travail de l'apprenant.
#
# Rejouable : tout est retiré puis reposé.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
MAISON="$(getent passwd "$LAB_USER" | cut -d: -f6)"
DOSSIER="$MAISON/livraison"
MEMOIRE=/var/lib/dsoxlab/challenge-livrer-avec-helm-et-gitops.json
REGISTRE="registry:3.1.2@sha256:38907510915c3f1604c7e83d6ab602ab3020d092f73bdaed8696773693ff768c"
NGINX="nginx:1.31.2@sha256:b5a9a3cfc86b81dd6f1458d53f2ad2b559cc255653d2efd6cacee5636bf2066f"
HOTE_GIT=172.18.0.1
DEPOT=/srv/git/catalogue.git
CLE_ARGO=/root/.lab-livrer/argocd_ed25519

# ----------------------------------------------------------------------
# 0. Repartir de l'état d'origine
# ----------------------------------------------------------------------
helm --kubeconfig "$KUBECONFIG" uninstall vitrine -n vitrine --wait 2>/dev/null || true
kubectl -n argocd delete applications.argoproj.io --all --wait=true --timeout=120s 2>/dev/null || true
kubectl delete namespace vitrine catalogue registre --ignore-not-found --wait=true --timeout=180s
kubectl -n argocd delete secret depot-catalogue --ignore-not-found
rm -rf "$DOSSIER" "$DEPOT"
docker image ls --format '{{.Repository}}:{{.Tag}}' | { grep -E '^localhost:30500/' || true; } | xargs -r docker image rm -f

# ----------------------------------------------------------------------
# 1. Le registre
# ----------------------------------------------------------------------
kubectl create namespace registre
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: registre
  namespace: registre
spec:
  selector:
    matchLabels:
      app: registre
  template:
    metadata:
      labels:
        app: registre
    spec:
      containers:
        - name: registre
          image: ${REGISTRE}
          ports:
            - containerPort: 5000
---
apiVersion: v1
kind: Service
metadata:
  name: registre
  namespace: registre
spec:
  type: NodePort
  selector:
    app: registre
  ports:
    - port: 5000
      targetPort: 5000
      nodePort: 30500
EOF
kubectl -n registre rollout status deploy/registre --timeout=180s

# ----------------------------------------------------------------------
# 2. Le contexte de build, avec son jeton
# ----------------------------------------------------------------------
JETON=$(python3 -c 'import secrets; print(secrets.token_hex(6))')
mkdir -p /var/lib/dsoxlab
printf '{"jeton": "%s"}\n' "$JETON" > "$MEMOIRE"
chmod 0600 "$MEMOIRE"
install -d -o "$LAB_USER" -g "$LAB_USER" "$DOSSIER" "$DOSSIER/app"
cat > "$DOSSIER/app/index.html" <<EOF
<!doctype html>
<html lang="fr">
<head><meta charset="utf-8"><title>Vitrine</title></head>
<body><h1>Vitrine</h1><p>Construction ${JETON}</p></body>
</html>
EOF
cat > "$DOSSIER/app/Dockerfile" <<EOF
FROM ${NGINX}
COPY index.html /usr/share/nginx/html/index.html
EOF

# ----------------------------------------------------------------------
# 3. Le chart Helm local
# ----------------------------------------------------------------------
C="$DOSSIER/chart-vitrine"
mkdir -p "$C/templates"
cat > "$C/Chart.yaml" <<'EOF'
apiVersion: v2
name: vitrine
description: La vitrine de la boutique, servie par nginx.
type: application
version: 1.0.0
appVersion: "1.0"
EOF
cat > "$C/values.yaml" <<'EOF'
# Nombre d'exemplaires de la vitrine.
replicaCount: 1

image:
  repository: nginx
  # Un tag, OU un digest (sha256:...). Le digest l'emporte s'il est renseigné.
  tag: "1.31.2"
  digest: ""

service:
  port: 80

# Le bandeau affiché en en-tête de la réponse HTTP X-Bandeau.
bandeau: "Bienvenue"
EOF
cat > "$C/templates/_helpers.tpl" <<'EOF'
{{- define "vitrine.image" -}}
{{- if .Values.image.digest -}}
{{ .Values.image.repository }}@{{ .Values.image.digest }}
{{- else -}}
{{ .Values.image.repository }}:{{ .Values.image.tag }}
{{- end -}}
{{- end -}}
EOF
cat > "$C/templates/deployment.yaml" <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}
  labels:
    app: {{ .Release.Name }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app: {{ .Release.Name }}
    spec:
      containers:
        - name: vitrine
          image: {{ include "vitrine.image" . }}
          ports:
            - containerPort: 80
          env:
            - name: BANDEAU
              value: {{ .Values.bandeau | quote }}
          readinessProbe:
            httpGet:
              path: /
              port: 80
EOF
cat > "$C/templates/service.yaml" <<'EOF'
apiVersion: v1
kind: Service
metadata:
  name: {{ .Release.Name }}
spec:
  selector:
    app: {{ .Release.Name }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: 80
EOF
helm lint "$C"

# ----------------------------------------------------------------------
# 4. Le dépôt Git, servi en SSH par le compte git
# ----------------------------------------------------------------------
getent group git > /dev/null || groupadd git
id git > /dev/null 2>&1 || useradd -m -d /srv/git -s /usr/bin/git-shell -g git git
install -d -o git -g git -m 0755 /srv/git
usermod -aG git "$LAB_USER"
git init --bare --shared=group -b main "$DEPOT"
git config --system --get-all safe.directory | grep -qx "$DEPOT" || git config --system --add safe.directory "$DEPOT"

# Le contenu de départ, poussé par un clone temporaire.
T=$(mktemp -d)
git clone -q "$DEPOT" "$T/c"
mkdir -p "$T/c/catalogue"
cat > "$T/c/catalogue/deployment.yaml" <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: catalogue
spec:
  replicas: 1
  selector:
    matchLabels:
      app: catalogue
  template:
    metadata:
      labels:
        app: catalogue
    spec:
      containers:
        - name: catalogue
          image: ${NGINX}
          ports:
            - containerPort: 80
EOF
cat > "$T/c/catalogue/service.yaml" <<'EOF'
apiVersion: v1
kind: Service
metadata:
  name: catalogue
spec:
  selector:
    app: catalogue
  ports:
    - port: 80
      targetPort: 80
EOF
git -C "$T/c" -c user.name=Plateforme -c user.email=plateforme@example.org add -A
git -C "$T/c" -c user.name=Plateforme -c user.email=plateforme@example.org commit -q -m "catalogue : premier déploiement"
git -C "$T/c" push -q origin main
rm -rf "$T"
chown -R git:git "$DEPOT"
chmod -R g+rwX "$DEPOT"
find "$DEPOT" -type d -exec chmod g+s {} +

# Le clone de travail de l'apprenant.
sudo -u "$LAB_USER" git clone -q "$DEPOT" "$DOSSIER/catalogue"
sudo -u "$LAB_USER" git -C "$DOSSIER/catalogue" config user.name "$LAB_USER"
sudo -u "$LAB_USER" git -C "$DOSSIER/catalogue" config user.email "$LAB_USER@k8s-kind.lab"

# ----------------------------------------------------------------------
# 5. Les accès d'Argo CD au dépôt
# ----------------------------------------------------------------------
install -d -m 0700 "$(dirname "$CLE_ARGO")"
[[ -f "$CLE_ARGO" ]] || ssh-keygen -q -t ed25519 -N "" -C argocd-catalogue -f "$CLE_ARGO"
install -d -o git -g git -m 0700 /srv/git/.ssh
printf 'no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty %s\n' "$(cat "$CLE_ARGO.pub")" \
  > /srv/git/.ssh/authorized_keys
chown git:git /srv/git/.ssh/authorized_keys
chmod 0600 /srv/git/.ssh/authorized_keys

URL="ssh://git@${HOTE_GIT}${DEPOT}"
kubectl -n argocd create secret generic depot-catalogue \
  --from-literal=type=git --from-literal=url="$URL" \
  --from-file=sshPrivateKey="$CLE_ARGO"
kubectl -n argocd label secret depot-catalogue argocd.argoproj.io/secret-type=repository

# La clé d'hôte de la VM est passée à Argo CD par les values du chart, dans
# setup.yaml : un ConfigMap géré par Helm ne se modifie pas à la main.

python3 - "$MEMOIRE" "$URL" <<'PY'
import json
import sys
chemin, url = sys.argv[1], sys.argv[2]
with open(chemin, encoding="utf-8") as f:
    memoire = json.load(f)
memoire["depot"] = url
with open(chemin, "w", encoding="utf-8") as f:
    json.dump(memoire, f)
PY
chown -R "$LAB_USER:$LAB_USER" "$DOSSIER"
echo "Situation posee : registre, contexte de build, chart, depot $URL."
