#!/usr/bin/env bash
# Solution du formateur. Rejouée sur le control plane après `dsoxlab run`,
# elle prouve que le lab est FAISABLE et que ses tests passent quand le
# travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le volume, la réclamation, le Pod. La StorageClass manual n'existe pas
#    comme objet : le nom suffit à apparier PV et PVC.
cat <<'EOF' | $K apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: lab-pv
spec:
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  storageClassName: manual
  hostPath:
    path: /mnt/lab-data
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: lab-pvc
  namespace: lab
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: manual
  resources:
    requests:
      storage: 500Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: data-pod
  namespace: lab
spec:
  containers:
    - name: writer
      image: busybox:1.37
      command: ["sh", "-c", "echo hello > /data/test.txt && sleep infinity"]
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: lab-pvc
EOF

# 2. La liaison, le montage, le fichier.
$K -n lab wait --for=jsonpath='{.status.phase}'=Bound pvc/lab-pvc --timeout=60s
$K -n lab wait --for=condition=Ready pod/data-pod --timeout=180s
$K get pv lab-pv
$K -n lab exec data-pod -- cat /data/test.txt

# 3. Le fichier est sur le disque du nœud qui porte le Pod.
NOEUD="$($K -n lab get pod data-pod -o jsonpath='{.spec.nodeName}')"
if [[ "${NOEUD}" == "k8s-cp.lab" ]]; then
  sudo cat /mnt/lab-data/test.txt
else
  ssh -n "${NOEUD}" 'sudo cat /mnt/lab-data/test.txt'
fi
echo "lab-pvc est lié à lab-pv, data-pod a écrit hello, et le fichier est sur ${NOEUD}."
