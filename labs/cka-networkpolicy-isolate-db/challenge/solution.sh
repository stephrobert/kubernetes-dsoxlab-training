#!/usr/bin/env bash
# Solution du formateur. Rejouée sur le control plane après `dsoxlab run`,
# elle prouve que le lab est FAISABLE et que ses tests passent quand le
# travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Avant : tout le monde passe.
$K -n database exec frontend -- nc -z -w 3 db 5432 && echo "frontend passe, avant"

# 2. La politique : la base, en entrée, depuis les Pods app=backend du
#    namespace, sur 5432. Pas de namespaceSelector : intrus reste dehors.
cat <<'EOF' | $K apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-allow-backend
  namespace: database
spec:
  podSelector:
    matchLabels:
      app: db
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: backend
      ports:
        - protocol: TCP
          port: 5432
EOF

# 3. Après : le backend passe, les deux autres non.
sleep 3
$K -n database exec backend -- nc -z -w 3 db 5432 && echo "backend passe"
$K -n database exec frontend -- nc -z -w 3 db 5432 || echo "frontend bloqué"
$K -n autre exec intrus -- nc -z -w 3 db.database.svc.cluster.local 5432 || echo "intrus bloqué"
$K -n database exec db -- nslookup kubernetes.default.svc.cluster.local >/dev/null && echo "db résout toujours"
echo "Seul backend, dans database, atteint la base."
