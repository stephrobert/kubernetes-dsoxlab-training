#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
# `pipefail` est volontairement ABSENT ici, et c'est une correction.
#
# Mesuré le 2026-09-16 : `trivy image ... | head -12` fait recevoir SIGPIPE à
# trivy quand head a lu ses douze lignes et ferme le tuyau. Le script rendait
# alors 141, soit 128 + 13, et le validateur concluait « la solution du
# formateur a échoué » alors qu'elle avait fait son travail. Un scan tronqué
# pour l'affichage ne doit pas faire échouer une démonstration.
set -eu

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NS=chaine-appro

# 1. Constater. Le scan de l'image en production donne la mesure du problème.
echo "--- ce que porte nginx:1.21 ---"
sudo trivy image --quiet --scanners vuln --severity CRITICAL,HIGH nginx:1.21 2>/dev/null | head -12 || true

# 2. Choisir un remplacement, et le vérifier AVANT de le déployer. C'est
#    l'ordre qui compte : déployer puis scanner, c'est scanner en production.
echo "--- ce que porte nginx:1.27-alpine ---"
sudo trivy image --quiet --scanners vuln --severity CRITICAL,HIGH nginx:1.27-alpine 2>/dev/null | head -12 || true

# 3. Remplacer. `set image` suffit, et c'est le geste attendu à l'examen.
$K -n "$NS" set image deployment/web web=nginx:1.27-alpine
$K -n "$NS" rollout status deployment/web --timeout=300s

$K -n "$NS" get deployment web -o jsonpath='{.spec.template.spec.containers[0].image}'; echo
echo "L'image de production est remplacée, et le second scan le justifie."
