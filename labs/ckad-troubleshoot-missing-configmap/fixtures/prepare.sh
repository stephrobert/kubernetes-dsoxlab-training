#!/usr/bin/env bash
# Pose la situation : un Pod dont le volume référence un ConfigMap qui
# n'existe pas. Il reste en ContainerCreating, sans logs, avec des events.
#
# Rejouable : le namespace est attendu s'il se termine, le ConfigMap d'un
# passage précédent est retiré, et le Pod est recréé.
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

kubectl -n lab delete pod broken-app --ignore-not-found --wait=true
kubectl -n lab delete configmap app-settings --ignore-not-found

# L'application lit sa configuration, la copie dans sa page, puis sert.
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: broken-app
  namespace: lab
spec:
  containers:
    - name: app
      image: nginx:1.27-alpine
      command:
        - sh
        - -c
        - 'cat /config/settings.conf > /usr/share/nginx/html/index.html && exec nginx -g "daemon off;"'
      ports:
        - containerPort: 80
      volumeMounts:
        - name: config
          mountPath: /config
  volumes:
    - name: config
      configMap:
        name: app-settings
EOF

# On attend que le blocage soit visible dans les events.
for essai in $(seq 1 20); do
  if kubectl -n lab get events --field-selector involvedObject.name=broken-app 2>/dev/null | grep -q -i 'configmap'; then
    break
  fi
  sleep 3
done

echo "Situation posée : broken-app attend un ConfigMap qui n'existe pas."
