#!/usr/bin/env bash
# Pose l'application du lab k8s-relier-deux-clusters sur les deux clusters,
# depuis ha-cp1.lab (kubeconfig de cluster-2 posé par le setup) :
#
# - dans chaque cluster, le namespace mesh-demo, un Deployment echo qui répond
#   par le nom de SON cluster, et un Service echo ORDINAIRE (sans annotation
#   de service global) ;
# - dans cluster-1 seulement, le Pod client.
#
# Rien de ce que l'apprenant doit produire n'existe : les clusters ne sont pas
# reliés, et aucun Service n'est global. Le setup a remis les nœuds à zéro
# avant : ce script part de clusters neufs.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

BUSYBOX="busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e"
declare -A KUBECONFIGS=([1]=/etc/kubernetes/admin.conf [2]=/etc/kubernetes/cluster-2.conf)

for id in 1 2; do
  k="kubectl --kubeconfig ${KUBECONFIGS[$id]}"
  $k create namespace mesh-demo
  $k apply -f - <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
  namespace: mesh-demo
spec:
  replicas: 1
  selector:
    matchLabels: {app: echo}
  template:
    metadata:
      labels: {app: echo}
    spec:
      containers:
        - name: echo
          image: "$BUSYBOX"
          command: [sh, -c, 'echo reponse-de-cluster-$id > /tmp/index.html; httpd -f -p 8080 -h /tmp']
---
apiVersion: v1
kind: Service
metadata:
  name: echo
  namespace: mesh-demo
spec:
  selector: {app: echo}
  ports:
    - {port: 80, targetPort: 8080}
YAML
  $k -n mesh-demo rollout status deployment/echo --timeout=240s
done

kubectl --kubeconfig /etc/kubernetes/admin.conf apply -f - <<YAML
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: mesh-demo
spec:
  containers:
    - {name: client, image: "$BUSYBOX", command: [sleep, "36000"]}
YAML
kubectl --kubeconfig /etc/kubernetes/admin.conf -n mesh-demo wait --for=condition=Ready pod/client --timeout=180s
# Départ : seul cluster-1 répond.
for i in 1 2 3 4; do
  kubectl --kubeconfig /etc/kubernetes/admin.conf -n mesh-demo exec client -- wget -qO- -T 3 http://echo.mesh-demo/
done
echo "Situation posée : deux clusters non reliés, Service echo ordinaire des deux côtés."
