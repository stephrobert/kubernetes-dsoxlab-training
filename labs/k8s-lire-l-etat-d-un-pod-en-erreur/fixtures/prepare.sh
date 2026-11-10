#!/usr/bin/env bash
# Pose la situation : un namespace diagnostic neuf avec trois Deployments, dont
# deux en panne, et metrics-server pour que `kubectl top` réponde.
#
#   - web   : nginx épinglé, 2 réplicas, sain ;
#   - api   : image nginx:1.280, qui n'existe pas (ImagePullBackOff) ;
#   - batch : busybox qui écrit une erreur sur stderr puis sort en code 1
#             (CrashLoopBackOff).
#
# Rejouable : le namespace est recréé à chaque passage, pour que les
# Deployments repartent de leur génération 1, celle que le test « rien n'a été
# réparé » attend.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NS=diagnostic
WEB_IMAGE="nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
BATCH_IMAGE="busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e"
MS_VERSION=v0.9.1
MS_IMAGE="registry.k8s.io/metrics-server/metrics-server:v0.9.1@sha256:9b0ba1926e1d3089673f45461c3c1416109dea33b3ba3434048defd380df329b"
LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"

# 1. Un namespace neuf.
# --ignore-not-found plutôt qu'un get préalable : un namespace encore en
# Terminating au moment du get disparaîtrait avant le delete (NotFound, set -e).
kubectl delete namespace "$NS" --ignore-not-found --wait=true --timeout=180s
kubectl create namespace "$NS"

# 2. Les trois Deployments.
kubectl -n "$NS" create deployment web --image="$WEB_IMAGE" --replicas=2
# ❌ Image volontairement inexistante : c'est la première panne à diagnostiquer.
kubectl -n "$NS" create deployment api --image=nginx:1.280
kubectl -n "$NS" create deployment batch --image="$BATCH_IMAGE" \
  -- sh -c 'echo "batch: démarrage"; echo "erreur: variable DB_HOST absente" >&2; exit 1'

# 3. metrics-server, avec --kubelet-insecure-tls (les kubelets de kind
#    présentent un certificat que metrics-server ne sait pas vérifier) et son
#    image épinglée par digest. Réappliquer le manifeste remet son état publié,
#    le patch le corrige à chaque passage : le résultat est le même.
kubectl apply -f "https://github.com/kubernetes-sigs/metrics-server/releases/download/${MS_VERSION}/components.yaml"
kubectl -n kube-system patch deployment metrics-server --type=json -p "[
  {\"op\":\"add\",\"path\":\"/spec/template/spec/containers/0/args/-\",\"value\":\"--kubelet-insecure-tls\"},
  {\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/0/image\",\"value\":\"${MS_IMAGE}\"}
]"
kubectl -n kube-system rollout status deployment metrics-server --timeout=180s
kubectl -n "$NS" rollout status deployment web --timeout=180s

# 4. Attendre que l'API de métriques mesure les Pods de web : sans mesure, le
#    critère « Pod le plus gourmand » n'aurait rien à comparer.
for _ in $(seq 1 30); do
  if kubectl top pods -n "$NS" --no-headers 2>/dev/null | grep -q '^web-'; then
    break
  fi
  sleep 5
done
kubectl top pods -n "$NS" --no-headers

# 5. Le répertoire des livrables, vide, à l'apprenant.
rm -rf "${LAB_HOME}/diagnostic"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/diagnostic"

echo "Situation posée : api et batch ne démarrent pas, ${LAB_HOME}/diagnostic attend api.txt, batch.txt et top.txt."
