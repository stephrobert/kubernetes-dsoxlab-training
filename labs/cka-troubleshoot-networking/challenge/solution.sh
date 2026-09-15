#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le diagnostic, dans l'ordre : endpoints, selector et ports, labels des
#    Pods, politiques.
$K -n lab get endpointslices -l kubernetes.io/service-name=web-svc
$K -n lab get service web-svc -o jsonpath='{.spec.selector}{" "}{.spec.ports}{"\n"}'
$K -n lab get pods -l app=web --show-labels | head -3
$K -n lab get networkpolicy

# 2. Le Service : le selector des Pods, et le port où nginx écoute.
$K -n lab patch service web-svc --type=merge \
  -p '{"spec":{"selector":{"app":"web"},"ports":[{"port":80,"targetPort":80,"protocol":"TCP"}]}}'

# 3. Rouvrir exactement ce qu'il faut : le port 80 des Pods app=web, depuis
#    toute source. block-all reste, les politiques s'additionnent.
cat <<'YAML' | $K apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-web-ingress
  namespace: lab
spec:
  podSelector:
    matchLabels:
      app: web
  policyTypes:
    - Ingress
  ingress:
    - ports:
        - protocol: TCP
          port: 80
YAML

# 4. La preuve, depuis le client, par le nom du Service.
for essai in $(seq 1 15); do
  if $K -n lab exec client -- wget -qO- -T 5 http://web-svc/ >/dev/null 2>&1; then
    break
  fi
  sleep 3
done
$K -n lab exec client -- wget -qO- -T 5 http://web-svc/ | grep -i -m1 'nginx'
echo "web-svc dessert web-app, et le client le joint malgré block-all."
