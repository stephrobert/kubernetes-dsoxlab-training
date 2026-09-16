#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -eu

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Constater l'état de départ : le contrôleur sert SON certificat.
echo -n "avant : "
echo | openssl s_client -connect 127.0.0.1:30443 -servername vitrine.lab 2>/dev/null \
  | openssl x509 -noout -subject || echo "pas de certificat"

# 2. Fabriquer un certificat au nom de l'hôte.
#
#    Le SAN n'est pas décoratif : depuis des années, les clients TLS ignorent
#    le CN et ne valident QUE le subjectAltName. Un certificat qui n'aurait
#    que son CN serait refusé par un client qui vérifie, et le lab ne
#    l'accepte pas non plus.
TRAVAIL=$(mktemp -d)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$TRAVAIL/tls.key" -out "$TRAVAIL/tls.crt" \
  -subj '/CN=vitrine.lab' -addext 'subjectAltName=DNS:vitrine.lab' 2>/dev/null

# 3. Le déposer dans un Secret du type attendu. Le type compte : un Secret
#    générique portant les mêmes clés ne serait pas lu par le contrôleur.
$K -n vitrine create secret tls vitrine-tls \
  --cert="$TRAVAIL/tls.crt" --key="$TRAVAIL/tls.key" \
  --dry-run=client -o yaml | $K apply -f -
rm -rf "$TRAVAIL"

# 4. Le déclarer dans l'Ingress. C'est cette section qui dit au contrôleur
#    quel certificat présenter pour quel hôte.
cat <<'YAML' | $K apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: site
  namespace: vitrine
spec:
  ingressClassName: traefik
  tls:
    - hosts:
        - vitrine.lab
      secretName: vitrine-tls
  rules:
    - host: vitrine.lab
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: site
                port:
                  number: 80
YAML

# Le contrôleur recharge sa configuration après avoir été notifié : la
# bascule n'est pas immédiate.
sleep 10

# 5. La preuve.
echo -n "après : "
echo | openssl s_client -connect 127.0.0.1:30443 -servername vitrine.lab 2>/dev/null \
  | openssl x509 -noout -subject
echo -n "le site répond toujours : "
curl -sk -o /dev/null -w '%{http_code}\n' --resolve vitrine.lab:30443:127.0.0.1 \
  https://vitrine.lab:30443/ --max-time 10
