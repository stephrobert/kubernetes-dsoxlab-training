#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -eu

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Constater l'état de départ : le lecteur ne voit pas le fichier.
echo -n "avant, le lecteur voit le fichier : "
$K -n journalisation exec collecteur -c lecteur -- sh -c 'test -f /var/trace/messages' >/dev/null 2>&1 \
  && echo "oui" || echo "non"

# 2. Le volume partagé.
#
#    `emptyDir` naît avec le Pod et meurt avec lui : il ne sert pas à
#    conserver, mais à FAIRE PASSER. C'est exactement ce qu'il faut entre deux
#    conteneurs d'un même Pod, et c'est ce qui le distingue d'une revendication
#    de volume persistant.
#
#    Les champs d'un Pod ne se modifient pas tous à chaud : celui-ci est
#    recréé.
$K -n journalisation delete pod collecteur --ignore-not-found --wait=true
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: collecteur
  namespace: journalisation
spec:
  volumes:
    - name: trace
      emptyDir: {}
  containers:
    - name: producteur
      image: busybox:1.37
      command:
        - sh
        - -c
        - "mkdir -p /var/trace; while true; do echo \"trace $(date +%s)\" >> /var/trace/messages; sleep 5; done"
      volumeMounts:
        - name: trace
          mountPath: /var/trace
    - name: lecteur
      image: busybox:1.37
      command: ["sh", "-c", "sleep 86400"]
      volumeMounts:
        - name: trace
          mountPath: /var/trace
          readOnly: true
YAML

$K -n journalisation wait --for=condition=ready pod/collecteur --timeout=240s
# Le producteur écrit toutes les cinq secondes : on lui laisse un tour.
sleep 8

# 3. La preuve, dans les deux sens.
echo -n "après, le lecteur voit le fichier du volume : "
$K -n journalisation exec collecteur -c lecteur -- sh -c 'test -s /var/trace/messages' >/dev/null 2>&1 \
  && echo "oui" || echo "NON, anormal"
echo -n "après, un fichier écrit HORS du volume traverse : "
$K -n journalisation exec collecteur -c producteur -- sh -c 'echo prive > /var/hors-volume' >/dev/null 2>&1
$K -n journalisation exec collecteur -c lecteur -- sh -c 'test -f /var/hors-volume' >/dev/null 2>&1 \
  && echo "OUI, anormal" || echo "non, normal"
