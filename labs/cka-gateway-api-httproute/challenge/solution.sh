#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -eu

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Constater l'état de départ : rien ne route.
echo -n "avant, /api : "
curl -s --resolve app.local:30080:127.0.0.1 http://app.local:30080/api \
  --max-time 8 -w ' [%{http_code}]\n' || echo "pas de réponse"

# 2. La Gateway, qui déclare le point d'entrée, puis la route qui s'y
#    attache. C'est la séparation qui fait tout l'intérêt de cette API :
#    l'exploitant du cluster tient la Gateway, les équipes applicatives
#    attachent leurs routes.
#
#    `allowedRoutes` dit QUI peut s'attacher. `Same` limite au namespace de
#    la Gateway, ce qui suffit ici et ne laisse rien d'ouvert.
cat <<'YAML' | $K apply -f -
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: lab-gateway
  namespace: lab
spec:
  gatewayClassName: traefik
  listeners:
    - name: http
      protocol: HTTP
      port: 80
      allowedRoutes:
        namespaces:
          from: Same
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: lab-routes
  namespace: lab
spec:
  parentRefs:
    - name: lab-gateway
  hostnames:
    - app.local
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /api
      backendRefs:
        - name: svc-api
          port: 80
    - matches:
        - path:
            type: PathPrefix
            value: /web
      backendRefs:
        - name: svc-web
          port: 80
YAML

# Le contrôleur programme la Gateway après avoir été notifié.
sleep 15

# 3. La preuve. L'état de la Gateway se lit dans ses conditions, ce qu'aucun
#    `get` sommaire ne montre : une Gateway acceptée mais non programmée ne
#    route rien.
echo -n "Programmed : "
$K -n lab get gateway lab-gateway \
  -o jsonpath='{.status.conditions[?(@.type=="Programmed")].status}'
echo
for chemin in /api /web /autre; do
  printf 'après, %-7s -> ' "$chemin"
  curl -s --resolve app.local:30080:127.0.0.1 "http://app.local:30080$chemin" \
    --max-time 8 -w ' [%{http_code}]\n'
done
