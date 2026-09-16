#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -eu

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Constater l'état de départ : l'intérieur du conteneur s'écrit.
POD=$($K -n catalogue get pod -l app=vitrine -o jsonpath='{.items[0].metadata.name}')
echo -n "avant, écriture dans /etc/nginx/conf.d : "
$K -n catalogue exec "$POD" -- sh -c 'touch /etc/nginx/conf.d/preuve' >/dev/null 2>&1 \
  && echo "acceptée" || echo "refusée"

# 2. Le durcissement.
#
#    readOnlyRootFilesystem ferme TOUT le système de fichiers de l'image. Ce
#    qui doit rester inscriptible se rouvre chemin par chemin, avec des
#    volumes éphémères : le contenu y est perdu au redémarrage du conteneur,
#    ce qui est exactement ce qu'on veut pour du cache et des fichiers
#    temporaires.
#
#    Les deux chemins nécessaires ont été mesurés le 2026-09-16 en refusant
#    d'abord de les monter : nginx s'arrête sur
#    « mkdir() "/tmp/proxy_temp" failed (30: Read-only file system) ».
#    /var/cache/nginx est monté pour la même raison, avant que le cache ne
#    serve.
cat <<'YAML' | $K apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitrine
  namespace: catalogue
spec:
  replicas: 2
  selector:
    matchLabels:
      app: vitrine
  template:
    metadata:
      labels:
        app: vitrine
    spec:
      securityContext:
        runAsNonRoot: true
      volumes:
        - name: cache
          emptyDir: {}
        - name: tmp
          emptyDir: {}
      containers:
        - name: web
          image: nginxinc/nginx-unprivileged:1.27-alpine
          ports:
            - containerPort: 8080
          securityContext:
            readOnlyRootFilesystem: true
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL
          volumeMounts:
            - name: cache
              mountPath: /var/cache/nginx
            - name: tmp
              mountPath: /tmp
YAML

$K -n catalogue rollout status deployment/vitrine --timeout=240s

# 3. La preuve, dans les deux sens.
POD=$($K -n catalogue get pod -l app=vitrine -o jsonpath='{.items[0].metadata.name}')
echo -n "après, écriture dans /etc/nginx/conf.d : "
$K -n catalogue exec "$POD" -- sh -c 'touch /etc/nginx/conf.d/preuve' >/dev/null 2>&1 \
  && echo "ACCEPTÉE, anormal" || echo "refusée"
echo -n "après, le site répond : "
$K -n catalogue exec client -- wget -qO- -T 5 http://vitrine.catalogue.svc.cluster.local/ >/dev/null 2>&1 \
  && echo "oui" || echo "NON, anormal"
echo -n "après, écriture dans un volume monté : "
$K -n catalogue exec "$POD" -- sh -c 'touch /tmp/ok' >/dev/null 2>&1 \
  && echo "acceptée, normal" || echo "refusée"
