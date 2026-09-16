#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -eu

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Constater l'état de départ : rien ne route.
echo -n "avant, /api : "
curl -s --resolve app.local:30080:127.0.0.1 http://app.local:30080/api \
  --max-time 8 -w ' [%{http_code}]\n' || echo "pas de réponse"

# 2. La règle de routage.
#
#    `pathType: Prefix` fait correspondre le chemin demandé au préfixe
#    déclaré. `Exact` n'accepterait que /api, pas /api/v1, ce qui casserait
#    la première requête réelle de l'application.
cat <<'YAML' | $K apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  namespace: lab
spec:
  ingressClassName: traefik
  rules:
    - host: app.local
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: svc-api
                port:
                  number: 80
          - path: /web
            pathType: Prefix
            backend:
              service:
                name: svc-web
                port:
                  number: 80
YAML

# Le contrôleur recharge sa configuration après avoir été notifié.
sleep 10

# 3. La preuve, sur les trois chemins.
for chemin in /api /web /autre; do
  printf 'après, %-7s -> ' "$chemin"
  curl -s --resolve app.local:30080:127.0.0.1 "http://app.local:30080$chemin" \
    --max-time 8 -w ' [%{http_code}]\n'
done
