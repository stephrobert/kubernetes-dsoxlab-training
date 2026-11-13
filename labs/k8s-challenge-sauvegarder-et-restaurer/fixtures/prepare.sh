#!/usr/bin/env bash
# Pose la situation du challenge, dans cet ordre :
#   1. le namespace facturation et son ConfigMap tarifs, UID notés ;
#   2. la sauvegarde « de la veille », avec eux dedans, datée d'hier ;
#   3. l'incident : facturation supprimé, puis un objet écrit APRÈS la
#      sauvegarde, qui doit disparaître à la restauration ;
#   4. un dépôt de manifestes en API retirées (autoscaling/v2beta2,
#      policy/v1beta1), dans ~/depot de l'utilisateur du lab ;
#   5. le certificat de l'API server réémis pour 20 jours seulement ;
#   6. l'état noté pour les tests, hors de la base, puis l'instantané de
#      secours du cleanup.
#
# Rejouable : remettre-etcd.sh a ramené le cluster sur /var/lib/etcd ; ici,
# tout ce que le challenge a écrit est refait de zéro.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

ETAT_DIR=/var/lib/dsoxlab
ETAT="${ETAT_DIR}/k8s-challenge-sauvegarder-et-restaurer.json"
SECOURS="${ETAT_DIR}/etcd-secours.db"
SAUVEGARDES=/var/backups/etcd
VEILLE="${SAUVEGARDES}/etcd-veille.db"
PKI=/etc/kubernetes/pki/etcd
ETCDCTL="etcdctl --endpoints=https://127.0.0.1:2379 --cacert=${PKI}/ca.crt --cert=${PKI}/healthcheck-client.crt --key=${PKI}/healthcheck-client.key"
MAISON="$(getent passwd "${LAB_USER}" | cut -d: -f6)"
DEPOT="${MAISON}/depot"

mkdir -p "${ETAT_DIR}"
chmod 700 "${ETAT_DIR}"
rm -rf "${SAUVEGARDES}" "${DEPOT}"
rm -f "${ETAT}"
mkdir -p "${SAUVEGARDES}"

# Ce qu'un passage précédent a pu laisser.
for ns in facturation depot; do
  if [[ "$(kubectl get namespace "${ns}" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
    kubectl wait --for=delete "namespace/${ns}" --timeout=180s
  fi
  kubectl delete namespace "${ns}" --ignore-not-found --wait=true --timeout=180s
done
kubectl -n default delete configmap intrus-apres-sauvegarde --ignore-not-found

# 1. Les données de la facturation.
kubectl create namespace facturation
kubectl -n facturation create configmap tarifs --from-literal=tva=20 --from-literal=devise=EUR
NS_UID="$(kubectl get namespace facturation -o jsonpath='{.metadata.uid}')"
CM_UID="$(kubectl -n facturation get configmap tarifs -o jsonpath='{.metadata.uid}')"

# 2. La sauvegarde de la veille, datée d'hier soir.
${ETCDCTL} snapshot save "${VEILLE}"
touch -d "yesterday 22:00" "${VEILLE}"
REV_VEILLE="$(etcdutl snapshot status "${VEILLE}" -w json | python3 -c 'import json,sys; print(json.load(sys.stdin)["revision"])')"

# 3. L'incident, puis un objet écrit après la sauvegarde.
kubectl delete namespace facturation --wait=true --timeout=180s
kubectl -n default create configmap intrus-apres-sauvegarde --from-literal=cree-le="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 4. Le dépôt : des manifestes en API retirées. Ils ne s'appliquent pas tels quels.
install -d -o "${LAB_USER}" -g "${LAB_USER}" "${DEPOT}"
cat > "${DEPOT}/00-namespace.yaml" <<'YAML'
apiVersion: v1
kind: Namespace
metadata:
  name: depot
YAML
cat > "${DEPOT}/10-catalogue.yaml" <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: catalogue
  namespace: depot
spec:
  replicas: 2
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
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sleep", "3600"]
          resources:
            requests:
              cpu: 10m
YAML
cat > "${DEPOT}/20-hpa.yaml" <<'YAML'
apiVersion: autoscaling/v2beta2
kind: HorizontalPodAutoscaler
metadata:
  name: catalogue
  namespace: depot
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: catalogue
  minReplicas: 2
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
YAML
cat > "${DEPOT}/30-pdb.yaml" <<'YAML'
apiVersion: policy/v1beta1
kind: PodDisruptionBudget
metadata:
  name: catalogue
  namespace: depot
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: catalogue
YAML
chown "${LAB_USER}:${LAB_USER}" "${DEPOT}"/*.yaml

# 5. Le certificat de l'API server, réémis pour 20 jours : kubeadm renouvelle
#    avec la durée de la configuration qu'on lui passe. Mesuré le 2026-11-13.
CONFIG="$(mktemp)"
kubectl -n kube-system get configmap kubeadm-config -o jsonpath='{.data.ClusterConfiguration}' > "${CONFIG}"
if grep -q '^certificateValidityPeriod:' "${CONFIG}"; then
  sed -i 's/^certificateValidityPeriod:.*/certificateValidityPeriod: 480h0m0s/' "${CONFIG}"
else
  echo "certificateValidityPeriod: 480h0m0s" >> "${CONFIG}"
fi
kubeadm certs renew apiserver --config "${CONFIG}"
rm -f "${CONFIG}"
openssl x509 -in /etc/kubernetes/pki/apiserver.crt -noout -enddate

# 6. L'état pour les tests, et l'instantané de secours du cleanup.
REVISION="$(${ETCDCTL} endpoint status -w json | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["Status"]["header"]["revision"])')"
python3 - "${ETAT}" "${NS_UID}" "${CM_UID}" "${REV_VEILLE}" "${REVISION}" <<'PY'
import json
import sys
import time
chemin, ns_uid, cm_uid, rev_veille, revision = sys.argv[1:]
json.dump({"ns_uid": ns_uid, "cm_uid": cm_uid, "revision_veille": int(rev_veille),
           "revision": int(revision), "epoch": int(time.time())}, open(chemin, "w"))
PY
chmod 600 "${ETAT}"
${ETCDCTL} snapshot save "${SECOURS}"
echo "challenge posé : facturation supprimé, sauvegarde de la veille dans ${VEILLE}"
