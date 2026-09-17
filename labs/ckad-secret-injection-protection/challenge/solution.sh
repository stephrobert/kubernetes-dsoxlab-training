#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -eu

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Constater l'état de départ : la valeur est dans le manifeste.
echo -n "avant, le manifeste contient le mot de passe : "
$K -n paiement get deployment passerelle -o yaml | grep -q 'Tr3s0r-2026' && echo "oui" || echo "non"

# 2. L'objet qui porte la valeur. `--from-literal` encode en base64 à votre
#    place : ce n'est PAS du chiffrement, seulement un transport. Ce que le
#    Secret change, c'est que la valeur cesse de vivre dans le manifeste de
#    l'application, où elle serait versionnée avec le reste.
$K -n paiement create secret generic passerelle-db \
  --from-literal=mot-de-passe='Tr3s0r-2026' \
  --dry-run=client -o yaml | $K apply -f -

# 3. L'injection, par les DEUX chemins demandés.
#
#    `secretKeyRef` injecte une clé dans une variable. Le montage en volume
#    dépose chaque clé comme un fichier portant son nom, ce qui permet à une
#    application de relire la valeur sans redémarrer, là où une variable est
#    figée pour la vie du processus.
cat <<'YAML' | $K apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: passerelle
  namespace: paiement
spec:
  replicas: 1
  selector:
    matchLabels:
      app: passerelle
  template:
    metadata:
      labels:
        app: passerelle
    spec:
      volumes:
        - name: secret
          secret:
            secretName: passerelle-db
      containers:
        - name: appli
          image: busybox:1.37
          command: ["sh", "-c", "sleep 86400"]
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: passerelle-db
                  key: mot-de-passe
          volumeMounts:
            - name: secret
              mountPath: /etc/passerelle
              readOnly: true
YAML

$K -n paiement rollout status deployment/passerelle --timeout=240s

# 4. La preuve, dans les deux sens.
POD=$($K -n paiement get pod -l app=passerelle -o jsonpath='{.items[0].metadata.name}')
echo -n "après, le manifeste contient le mot de passe : "
$K -n paiement get deployment passerelle -o yaml | grep -q 'Tr3s0r-2026' && echo "OUI, anormal" || echo "non"
echo -n "après, la variable dans le conteneur : "
$K -n paiement exec "$POD" -- sh -c 'echo "$DB_PASSWORD"'
echo -n "après, le fichier monté : "
$K -n paiement exec "$POD" -- cat /etc/passerelle/mot-de-passe; echo
