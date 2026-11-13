#!/usr/bin/env bash
# Pose le namespace atelier-tls et le certificat api-tls, cassé : il vise un
# émetteur ca-entreprise qui n'existe pas, et reste donc « not ready ». Aucun
# émetteur, aucune CA : c'est le travail.
# Rejouable : le namespace est recréé.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x
kubectl delete namespace atelier-tls --ignore-not-found --wait=true --timeout=180s
kubectl create namespace atelier-tls
# Le webhook de cert-manager peut refuser quelques secondes après son
# démarrage : on réessaie.
for essai in $(seq 1 20); do
  if cat <<'YAML' | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: api-tls
  namespace: atelier-tls
spec:
  secretName: api-tls
  dnsNames:
    - api.atelier-tls.svc
  issuerRef:
    name: ca-entreprise
    kind: Issuer
YAML
  then break; fi
  sleep 5
done
kubectl -n atelier-tls get certificate api-tls
echo "Lab posé : api-tls attend un émetteur qui n'existe pas."
