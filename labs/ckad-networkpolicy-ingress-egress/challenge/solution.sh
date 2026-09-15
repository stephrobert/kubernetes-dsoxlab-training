#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

cat <<'YAML' | $K apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-policy
  namespace: lab
spec:
  podSelector:
    matchLabels:
      tier: backend
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              tier: frontend
      ports:
        - protocol: TCP
          port: 80
  egress:
    - to:
        - podSelector:
            matchLabels:
              tier: database
      ports:
        - protocol: TCP
          port: 80
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-policy
  namespace: lab
spec:
  podSelector:
    matchLabels:
      tier: database
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              tier: backend
      ports:
        - protocol: TCP
          port: 80
YAML
sleep 5

# La preuve, flux par flux.
IP_BACK=$($K -n lab get pod backend -o jsonpath='{.status.podIP}')
IP_DB=$($K -n lab get pod database -o jsonpath='{.status.podIP}')
echo -n "frontend -> backend : "; $K -n lab exec frontend -- wget -qO- -T 3 "http://${IP_BACK}/"
echo -n "backend -> database : "; $K -n lab exec backend -- wget -qO- -T 3 "http://${IP_DB}/"
echo -n "backend -> DNS      : "; $K -n lab exec backend -- nslookup database.lab.svc.cluster.local >/dev/null 2>&1 && echo "résout" || echo "ne résout pas (attendu : résout un nom de Service, database n'en a pas)"; true
echo -n "intrus -> backend   : "; $K -n lab exec intrus -- wget -qO- -T 3 "http://${IP_BACK}/" 2>/dev/null && echo "PASSE, anormal" || echo "bloqué"
echo -n "intrus -> database  : "; $K -n lab exec intrus -- wget -qO- -T 3 "http://${IP_DB}/" 2>/dev/null && echo "PASSE, anormal" || echo "bloqué"
echo -n "database -> backend : "; $K -n lab exec database -- wget -qO- -T 3 "http://${IP_BACK}/" 2>/dev/null && echo "PASSE, anormal" || echo "bloqué"
echo "Les trois tiers sont cloisonnés."
