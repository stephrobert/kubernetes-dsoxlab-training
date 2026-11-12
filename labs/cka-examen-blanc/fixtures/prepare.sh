#!/usr/bin/env bash
# Pose l'examen blanc CKA sur le cluster kubeadm du catalogue, AVANT que le
# setup ne mette k8s-w1 hors service (tâche 3). Le worker porte déjà le taint de
# la tâche 9 : tout ce qui est posé ici tourne sur le control plane.
#
#   - trois contextes dans le kubeconfig de l'apprenant, vers ce même cluster :
#     cka-infra (namespace default), cka-appli (appli), cka-reseau (reseau) ;
#   - ~/examen/ : la CRD fournie et l'arbre Kustomize à compléter ;
#   - l'état de départ de chaque tâche, faux par construction.
#
# Rejouable : les namespaces sont attendus s'ils se terminent, puis recréés.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
FIX=/var/lib/dsoxlab/cka-examen
NGINX="nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
ECHO="hashicorp/http-echo:1.0.0@sha256:fcb75f691c8b0414d670ae570240cbf95502cc18a9ba57e982ecac589760a186"
BUSYBOX="busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
POSTGRES="postgres:18.6-alpine@sha256:9ba53c7d41ea093baf5c1ba635ba5434c4f979880527d49bb7d9237d3193085b"

for ns in appli reseau prod; do
  if [[ "$(kubectl get namespace "$ns" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
    kubectl wait --for=delete "namespace/$ns" --timeout=240s
  fi
  kubectl get namespace "$ns" >/dev/null 2>&1 || kubectl create namespace "$ns"
done

# Les contextes de l'examen, dans le kubeconfig de l'apprenant.
CONF="${LAB_HOME}/.kube/config"
for ctx in cka-infra:default cka-appli:appli cka-reseau:reseau; do
  sudo -u "$LAB_USER" kubectl --kubeconfig "$CONF" config set-context "${ctx%%:*}" \
    --cluster=kubernetes --user=kubernetes-admin --namespace="${ctx##*:}"
done
sudo -u "$LAB_USER" kubectl --kubeconfig "$CONF" config use-context kubernetes-admin@kubernetes

# Les fichiers fournis.
rm -rf "${LAB_HOME}/examen"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/examen"
cp "$FIX/crd-sauvegarde.yaml" "${LAB_HOME}/examen/"
cp -r "$FIX/kustomize" "${LAB_HOME}/examen/"
chown -R "$LAB_USER:$LAB_USER" "${LAB_HOME}/examen"

# Tâche 6 : un journal dont les lignes ERROR sont tirées au hasard.
JOURNAL="$(mktemp)"
mots=(paiement stock livraison panier facture compte remise retour)
for i in $(seq 1 14); do
  mot="${mots[$((RANDOM % ${#mots[@]}))]}"
  if (( RANDOM % 3 == 0 )); then
    echo "2026-11-12T10:$((10 + i)):00Z ERROR ${mot} : échec numéro $((RANDOM % 900 + 100))" >> "$JOURNAL"
  else
    echo "2026-11-12T10:$((10 + i)):00Z INFO ${mot} : traité" >> "$JOURNAL"
  fi
done
grep -q ERROR "$JOURNAL" || echo "2026-11-12T10:30:00Z ERROR stock : échec numéro 404" >> "$JOURNAL"
kubectl -n appli create configmap journal-texte --from-file=journal.log="$JOURNAL" --dry-run=client -o yaml | kubectl apply -f -
rm -f "$JOURNAL"

cat <<YAML | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: facture
  namespace: appli
spec:
  replicas: 2
  selector:
    matchLabels:
      app: facture
  template:
    metadata:
      labels:
        app: facture
    spec:
      containers:
        - name: web
          image: ${NGINX}
          command: ["nginx-demarrer"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: annuaire
  namespace: appli
spec:
  replicas: 2
  selector:
    matchLabels:
      app: annuaire
  template:
    metadata:
      labels:
        app: annuaire
    spec:
      containers:
        - name: echo
          image: ${ECHO}
          args: ["-text=annuaire", "-listen=:5678"]
---
apiVersion: v1
kind: Service
metadata:
  name: annuaire
  namespace: appli
spec:
  selector:
    app: annuaires
  ports:
    - port: 80
      targetPort: 5678
---
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: appli
spec:
  containers:
    - name: shell
      image: ${BUSYBOX}
      command: ["sleep", "infinity"]
---
apiVersion: v1
kind: Pod
metadata:
  name: journal
  namespace: appli
spec:
  containers:
    - name: app
      image: ${BUSYBOX}
      command: ["sh", "-c", "cat /texte/journal.log; sleep infinity"]
      volumeMounts:
        - name: texte
          mountPath: /texte
  volumes:
    - name: texte
      configMap:
        name: journal-texte
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitrine
  namespace: appli
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
      containers:
        - name: web
          image: ${NGINX}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: appli
spec:
  replicas: 1
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: app
          image: ${BUSYBOX}
          command: ["sleep", "infinity"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rapport
  namespace: appli
spec:
  replicas: 2
  selector:
    matchLabels:
      app: rapport
  template:
    metadata:
      labels:
        app: rapport
    spec:
      containers:
        - name: web
          image: ${NGINX}
---
apiVersion: v1
kind: Pod
metadata:
  name: db
  namespace: reseau
  labels:
    app: db
spec:
  containers:
    - name: postgres
      image: ${POSTGRES}
      env:
        - name: POSTGRES_PASSWORD
          value: lab-seulement
      ports:
        - containerPort: 5432
---
apiVersion: v1
kind: Service
metadata:
  name: db
  namespace: reseau
spec:
  selector:
    app: db
  ports:
    - port: 5432
      targetPort: 5432
---
apiVersion: v1
kind: Pod
metadata:
  name: front
  namespace: reseau
  labels:
    app: front
spec:
  containers:
    - name: shell
      image: ${BUSYBOX}
      command: ["sleep", "infinity"]
---
apiVersion: v1
kind: Pod
metadata:
  name: autre
  namespace: reseau
  labels:
    app: autre
spec:
  containers:
    - name: shell
      image: ${BUSYBOX}
      command: ["sleep", "infinity"]
YAML

for app in api web accueil; do
cat <<YAML | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${app}
  namespace: reseau
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ${app}
  template:
    metadata:
      labels:
        app: ${app}
    spec:
      containers:
        - name: echo
          image: ${ECHO}
          args: ["-text=${app}", "-listen=:5678"]
YAML
done
for app in api web; do
cat <<YAML | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: ${app}
  namespace: reseau
spec:
  selector:
    app: ${app}
  ports:
    - port: 80
      targetPort: 5678
YAML
done

kubectl -n appli rollout status deployment/annuaire deployment/vitrine deployment/api deployment/rapport --timeout=300s
kubectl -n appli wait --for=condition=Ready pod/client pod/journal --timeout=180s
kubectl -n reseau rollout status deployment/api deployment/web deployment/accueil --timeout=300s
kubectl -n reseau wait --for=condition=Ready pod/db pod/front pod/autre --timeout=240s

# La situation : tout le monde joint la base, et l'annuaire n'a aucun endpoint.
for essai in $(seq 1 20); do
  kubectl -n reseau exec autre -- nc -z -w 3 db 5432 && break
  sleep 3
done
kubectl -n reseau exec autre -- nc -z -w 3 db 5432
test -z "$(kubectl -n appli get endpointslices -l kubernetes.io/service-name=annuaire \
  -o jsonpath='{.items[*].endpoints[*].addresses[*]}')"
echo "Examen posé : trois namespaces, trois contextes, les pannes en place."
