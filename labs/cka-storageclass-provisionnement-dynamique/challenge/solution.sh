#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -eu

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Constater l'état de départ.
echo -n "avant, état de la revendication : "
$K -n archives get pvc donnees -o jsonpath='{.status.phase}'; echo

# 2. La revendication, cette fois rattachée à une classe.
#
#    Le champ `storageClassName` d'une revendication ne se modifie pas : elle
#    est recréée. Une chaîne VIDE n'est pas la même chose qu'un champ absent :
#    la première désactive explicitement le provisionnement dynamique, la
#    seconde laisse jouer la classe par défaut du cluster.
$K -n archives delete pvc donnees --ignore-not-found --wait=true
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: donnees
  namespace: archives
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: local-path
  resources:
    requests:
      storage: 128Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: registre
  namespace: archives
spec:
  volumes:
    - name: donnees
      persistentVolumeClaim:
        claimName: donnees
  containers:
    - name: appli
      image: busybox:1.37
      command: ["sh", "-c", "echo enregistre > /data/temoin; sleep 86400"]
      volumeMounts:
        - name: donnees
          mountPath: /data
YAML

# La classe est en WaitForFirstConsumer : la revendication ne se lie QU'AU
# MOMENT où un Pod l'utilise, et pas avant. Attendre la liaison sans avoir
# créé le Pod serait attendre pour rien.
$K -n archives wait --for=condition=ready pod/registre --timeout=300s

# 3. La preuve.
echo -n "après, état de la revendication : "
$K -n archives get pvc donnees -o jsonpath='{.status.phase}'; echo
echo -n "volume créé automatiquement : "
$K -n archives get pvc donnees -o jsonpath='{.spec.volumeName}'; echo
echo -n "le Pod a écrit dedans : "
$K -n archives exec registre -- cat /data/temoin
echo -n "ce que la classe décide à la suppression : "
$K get storageclass local-path -o jsonpath='{.reclaimPolicy}'; echo
