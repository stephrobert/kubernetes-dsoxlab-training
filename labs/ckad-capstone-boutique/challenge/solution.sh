#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le capstone est FAISABLE et que ses dix tests passent quand le travail
# est fait.
#
# C'est UNE solution, pas LA solution : le cahier des charges ne nomme aucun
# objet, et un candidat qui arriverait au même état par un autre chemin
# passerait les mêmes tests. C'est le propre d'un capstone.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NS=boutique

# Exigences 2 et 3 : la configuration et le secret vivent en dehors du Pod.
# Le Secret est créé par la CLI plutôt qu'écrit en YAML : c'est le geste de
# l'examen, et cela évite d'avoir à encoder la valeur en base64 à la main.
$K -n "$NS" create configmap catalogue-config \
  --from-literal=message="Bienvenue dans la boutique" \
  --dry-run=client -o yaml | $K apply -f -
$K -n "$NS" create secret generic catalogue-db \
  --from-literal=password="s3cr3t-boutique" \
  --dry-run=client -o yaml | $K apply -f -

# Exigences 1, 2, 3, 4 et 5 : le Deployment.
#
# Le port du conteneur est 8080 et non 80 : l'image tourne en 101, et un
# processus non root ne peut pas ouvrir un port inférieur à 1024. Les deux
# sondes visent donc 8080, et c'est le Service qui présentera 80 au client.
cat <<'YAML' | $K apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: catalogue
  namespace: boutique
  labels:
    app: catalogue
spec:
  replicas: 2
  selector:
    matchLabels:
      app: catalogue
  template:
    metadata:
      labels:
        app: catalogue
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
      containers:
        - name: catalogue
          image: nginxinc/nginx-unprivileged:1.27-alpine
          ports:
            - containerPort: 8080
          env:
            - name: MESSAGE
              valueFrom:
                configMapKeyRef:
                  name: catalogue-config
                  key: message
          volumeMounts:
            - name: db
              mountPath: /etc/db
              readOnly: true
          readinessProbe:
            httpGet:
              path: /
              port: 8080
            initialDelaySeconds: 3
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
      volumes:
        - name: db
          secret:
            secretName: catalogue-db
YAML
$K -n "$NS" rollout status deployment/catalogue --timeout=180s

# Exigence 6, premier temps : le nom stable. Le Service présente 80 au client
# et renvoie sur le 8080 du conteneur.
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: Service
metadata:
  name: catalogue-svc
  namespace: boutique
spec:
  selector:
    app: catalogue
  ports:
    - name: http
      protocol: TCP
      port: 80
      targetPort: 8080
YAML

# Exigence 6, second temps : l'isolation. Le port nommé dans la politique est
# celui du CONTENEUR, 8080, parce qu'une NetworkPolicy s'applique au Pod et
# ignore le Service : le paquet a déjà été traduit quand il arrive. Nommer 80
# ici bloquerait tout, y compris le frontend.
cat <<'YAML' | $K apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: catalogue-policy
  namespace: boutique
spec:
  podSelector:
    matchLabels:
      app: catalogue
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: frontend
      ports:
        - protocol: TCP
          port: 8080
YAML
sleep 5

# La preuve, exigence par exigence.
POD=$($K -n "$NS" get pods -l app=catalogue -o jsonpath='{.items[0].metadata.name}')
echo -n "identité du processus      : "; $K -n "$NS" exec "$POD" -- id -u
echo -n "message reçu               : "; $K -n "$NS" exec "$POD" -- printenv MESSAGE
echo -n "mot de passe lu en fichier : "; $K -n "$NS" exec "$POD" -- cat /etc/db/password; echo
echo -n "frontend -> boutique       : "
$K -n "$NS" exec frontend -- wget -qO- -T 5 http://catalogue-svc/ >/dev/null \
  && echo "passe" || echo "BLOQUÉ, anormal"
echo -n "intrus   -> boutique       : "
$K -n "$NS" exec intrus -- wget -qO- -T 5 http://catalogue-svc/ >/dev/null 2>&1 \
  && echo "PASSE, anormal" || echo "bloqué"
echo "La boutique est livrée : deux copies, configurée, secrète, surveillée, non root et cloisonnée."
