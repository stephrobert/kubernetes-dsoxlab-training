#!/usr/bin/env bash
# Pose la situation : trois Pods qui meurent chacun pour une raison
# différente. Une commande introuvable, une variable exigée et absente, une
# limite de mémoire que nginx dépasse dès le démarrage.
#
# Rejouable : le namespace est attendu s'il se termine, et les trois Pods
# sont supprimés puis recréés cassés.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace lab -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/lab --timeout=180s
fi
kubectl get namespace lab >/dev/null 2>&1 || kubectl create namespace lab

kubectl -n lab delete pod bad-command missing-env oom-killed --ignore-not-found --wait=true

cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: bad-command
  namespace: lab
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["serve-forever", "--port", "8080"]
---
apiVersion: v1
kind: Pod
metadata:
  name: missing-env
  namespace: lab
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "if [ -z \"$APP_MODE\" ]; then echo 'APP_MODE est obligatoire, arrêt' >&2; exit 1; fi; echo \"démarré en mode $APP_MODE\"; while true; do sleep 3600; done"]
---
apiVersion: v1
kind: Pod
metadata:
  name: oom-killed
  namespace: lab
spec:
  containers:
    - name: app
      image: nginx:1.27-alpine
      resources:
        requests:
          memory: 5Mi
        limits:
          memory: 5Mi
EOF

# On attend que les trois boucles soient visibles.
for essai in $(seq 1 40); do
  n=$(kubectl -n lab get pods bad-command missing-env oom-killed \
    -o jsonpath='{range .items[*]}{.status.containerStatuses[0].state.waiting.reason}{"\n"}{end}' 2>/dev/null \
    | grep -c CrashLoopBackOff || true)
  if (( n >= 3 )); then
    break
  fi
  sleep 3
done

echo "Situation posée : trois Pods en CrashLoopBackOff, trois causes."
