#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -eu

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. La RuntimeClass. C'est l'objet qui fait le pont entre un nom que les Pods
#    emploient et un runtime que containerd connaît : le `handler` doit
#    correspondre EXACTEMENT au nom déclaré dans la configuration de
#    containerd, ici `runsc`.
cat <<'YAML' | $K apply -f -
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: runsc
YAML

# 2. Le Pod qui s'en sert.
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: confine
  namespace: bac-a-sable
spec:
  nodeName: k8s-cp.lab
  runtimeClassName: gvisor
  containers:
    - name: outil
      image: busybox:1.37
      command: ["sh", "-c", "sleep 86400"]
YAML
$K -n bac-a-sable wait --for=condition=ready pod/confine --timeout=180s

# 3. La preuve, et elle ne se truque pas : le noyau que voit le Pod.
echo -n "Pod confiné  : "
$K -n bac-a-sable exec confine -- cat /proc/version
echo -n "Pod ordinaire : "
$K -n bac-a-sable exec ordinaire -- cat /proc/version
echo -n "noyau du nœud : "
uname -r
echo "Le Pod confiné ne voit pas le noyau de la machine."
