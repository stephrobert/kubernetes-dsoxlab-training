#!/usr/bin/env bash
# Pose la boutique et l'incident, sur le cluster que setup.yaml vient de
# ramener en 1.36.4, worker joint. Dans cet ordre :
#
#   1. le dépôt git ~/epreuve/manifestes, quatre manifestes commités :
#        vitrine.yaml       la vitrine, deux exemplaires, sans sonde ni
#                           contrainte de répartition, et son Service ;
#        panier.yaml        sa configuration et le composant panier, qui
#                           cherche /etc/panier/panier.conf alors que la
#                           configuration est montée sur /etc/config : il
#                           sort en erreur, CrashLoopBackOff ;
#        vitrine-pdb.yaml   un budget en policy/v1beta1, API retirée en 1.25 ;
#        purge.yaml         une tâche planifiée en batch/v1beta1, retirée en
#                           1.25 ;
#      et ~/epreuve/constats/, vide, où l'apprenant consigne les causes ;
#   2. le namespace boutique, vitrine.yaml et panier.yaml appliqués TELS QUELS
#      depuis le dépôt, et un Pod sans contrôleur, temoin-maintenance, lié au
#      worker par nodeName : un drain du worker doit le faire partir ;
#   3. la sauvegarde « de la veille », avec tout cela dedans, datée d'hier ;
#   4. l'incident : boutique supprimé, puis un objet écrit APRÈS la sauvegarde,
#      apres-la-veille, qui doit disparaître à la restauration ;
#   5. l'état noté pour les tests, hors de la base : UID, révisions, date.
#
# Rejouable : tout ce que l'épreuve écrit est refait de zéro.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
MAISON="$(getent passwd "$LAB_USER" | cut -d: -f6)"
EPREUVE="${MAISON}/epreuve"
DEPOT="${EPREUVE}/manifestes"
ETAT_DIR=/var/lib/dsoxlab
ETAT="${ETAT_DIR}/k8s-epreuve-administrer-un-cluster.json"
SAUVEGARDES=/var/backups/etcd
VEILLE="${SAUVEGARDES}/etcd-veille.db"
PKI=/etc/kubernetes/pki/etcd
ETCDCTL="etcdctl --endpoints=https://127.0.0.1:2379 --cacert=${PKI}/ca.crt --cert=${PKI}/healthcheck-client.crt --key=${PKI}/healthcheck-client.key"
WORKER=k8s-w1.lab

mkdir -p "$ETAT_DIR"
chmod 700 "$ETAT_DIR"
rm -rf "$SAUVEGARDES" "$EPREUVE"
rm -f "$ETAT"
mkdir -p "$SAUVEGARDES"

# Ce qu'un passage précédent a pu laisser.
if [[ "$(kubectl get namespace boutique -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/boutique --timeout=180s
fi
kubectl delete namespace boutique --ignore-not-found --wait=true --timeout=180s
kubectl -n default delete configmap apres-la-veille --ignore-not-found
kubectl uncordon "$WORKER"
kubectl wait --for=condition=Ready "node/${WORKER}" --timeout=300s

# 1. Le dépôt de manifestes.
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "$EPREUVE" "$DEPOT" "${EPREUVE}/constats"

cat > "${DEPOT}/vitrine.yaml" <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitrine
  namespace: boutique
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
          image: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 20m
              memory: 32Mi
---
apiVersion: v1
kind: Service
metadata:
  name: vitrine
  namespace: boutique
spec:
  selector:
    app: vitrine
  ports:
    - port: 80
      targetPort: 80
YAML

cat > "${DEPOT}/panier.yaml" <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: panier-config
  namespace: boutique
data:
  panier.conf: |
    devise=EUR
    paiement=carte
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: panier
  namespace: boutique
spec:
  replicas: 2
  selector:
    matchLabels:
      app: panier
  template:
    metadata:
      labels:
        app: panier
    spec:
      containers:
        - name: panier
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command:
            - sh
            - -c
            - |
              if [ ! -f /etc/panier/panier.conf ]; then
                echo "panier : configuration introuvable : /etc/panier/panier.conf" >&2
                exit 1
              fi
              echo "panier : configuration lue"
              exec sleep infinity
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
          volumeMounts:
            - name: configuration
              mountPath: /etc/config
      volumes:
        - name: configuration
          configMap:
            name: panier-config
YAML

cat > "${DEPOT}/vitrine-pdb.yaml" <<'YAML'
apiVersion: policy/v1beta1
kind: PodDisruptionBudget
metadata:
  name: vitrine
  namespace: boutique
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: vitrine
YAML

cat > "${DEPOT}/purge.yaml" <<'YAML'
apiVersion: batch/v1beta1
kind: CronJob
metadata:
  name: purge
  namespace: boutique
spec:
  schedule: "15 3 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: purge
              image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
              command: ["sh", "-c", "echo purge des paniers abandonnés"]
YAML

chown -R "$LAB_USER:$LAB_USER" "$EPREUVE"
sudo -u "$LAB_USER" git -C "$DEPOT" init -q -b main
sudo -u "$LAB_USER" git -C "$DEPOT" config user.name "Équipe boutique"
sudo -u "$LAB_USER" git -C "$DEPOT" config user.email "boutique@boutique.lab"
sudo -u "$LAB_USER" git -C "$DEPOT" add vitrine.yaml panier.yaml vitrine-pdb.yaml purge.yaml
sudo -u "$LAB_USER" git -C "$DEPOT" commit -q -m "Manifestes de la boutique"

# 2. La boutique, telle que le dépôt la décrit, et le témoin sur le worker.
kubectl create namespace boutique
kubectl apply -f "${DEPOT}/vitrine.yaml" -f "${DEPOT}/panier.yaml"
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: temoin-maintenance
  namespace: boutique
spec:
  nodeName: k8s-w1.lab
  containers:
    - name: temoin
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "infinity"]
YAML
kubectl -n boutique rollout status deployment/vitrine --timeout=300s
kubectl -n boutique wait --for=condition=Ready pod/temoin-maintenance --timeout=180s

# La panne de panier doit être réelle avant la sauvegarde : un redémarrage au
# moins, constaté.
redemarre=0
for _ in $(seq 1 40); do
  redemarre="$(kubectl -n boutique get pods -l app=panier -o json | python3 -c 'import json,sys; print(max([c.get("restartCount", 0) for p in json.load(sys.stdin)["items"] for c in p["status"].get("containerStatuses") or []] or [0]))')"
  [[ "$redemarre" -ge 1 ]] && break
  sleep 3
done
if [[ "$redemarre" -lt 1 ]]; then
  echo "panier ne redémarre pas : la panne n'est pas posée." >&2
  exit 1
fi

NS_UID="$(kubectl get namespace boutique -o jsonpath='{.metadata.uid}')"
VITRINE_UID="$(kubectl -n boutique get deployment vitrine -o jsonpath='{.metadata.uid}')"
PANIER_UID="$(kubectl -n boutique get deployment panier -o jsonpath='{.metadata.uid}')"

# 3. La sauvegarde de la veille, datée d'hier soir.
${ETCDCTL} snapshot save "$VEILLE"
touch -d "yesterday 22:00" "$VEILLE"
REV_VEILLE="$(etcdutl snapshot status "$VEILLE" -w json | python3 -c 'import json,sys; print(json.load(sys.stdin)["revision"])')"

# 4. L'incident, puis un objet écrit après la sauvegarde.
kubectl delete namespace boutique --wait=true --timeout=180s
kubectl -n default create configmap apres-la-veille --from-literal=cree-le="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 5. L'état pour les tests.
REVISION="$(${ETCDCTL} endpoint status -w json | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["Status"]["header"]["revision"])')"
python3 - "$ETAT" "$NS_UID" "$VITRINE_UID" "$PANIER_UID" "$REV_VEILLE" "$REVISION" <<'PY'
import json
import sys
import time
chemin, ns_uid, vitrine_uid, panier_uid, rev_veille, revision = sys.argv[1:]
json.dump({"ns_uid": ns_uid, "vitrine_uid": vitrine_uid, "panier_uid": panier_uid,
           "revision_veille": int(rev_veille), "revision": int(revision),
           "epoch": int(time.time())}, open(chemin, "w"))
PY
chmod 600 "$ETAT"
ls -la "$SAUVEGARDES"
echo "Boutique supprimée, sauvegarde de la veille dans ${VEILLE}, révision ${REVISION}."
