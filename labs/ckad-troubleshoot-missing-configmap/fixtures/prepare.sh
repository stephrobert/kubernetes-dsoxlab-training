#!/usr/bin/env bash
# Pose la situation : un Pod dont le volume référence une ConfigMap qui
# n'existe pas. Il reste en ContainerCreating, sans logs, avec des events.
#
# Rejouable : le namespace est attendu s'il se termine, la ConfigMap d'un
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
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
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

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
rm -rf "${LAB_HOME:?}/broken-app"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/broken-app"
install -d -m 0755 /var/lib/dsoxlab
printf '{"uid": "%s"}\n' "$(kubectl -n lab get pod broken-app -o jsonpath='{.metadata.uid}')" \
  > /var/lib/dsoxlab/troubleshoot-missing-configmap.json

echo "Situation posée : broken-app attend une ConfigMap qui n'existe pas."
