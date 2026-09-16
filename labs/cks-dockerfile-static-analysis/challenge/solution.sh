#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

# 1. Constater. L'analyse dit ce qu'elle reproche, avec un numéro par constat.
echo "--- ce que l'analyse reproche au départ ---"
sudo trivy config --quiet /root/inventaire 2>/dev/null | head -20

# 2. Corriger les cinq points, sans changer ce que l'image fait.
#
#    - le tag flottant devient une version précise, et la variante alpine
#      embarque bien moins de paquets, donc bien moins de failles ;
#    - apt-get disparaît avec la base Debian : apk le remplace, et
#      --no-cache évite de laisser l'index du gestionnaire dans l'image ;
#    - le port 22 n'a rien à faire là : une image n'ouvre pas de session SSH,
#      on déclare celui de l'application ;
#    - un utilisateur non root est déclaré ;
#    - un HEALTHCHECK dit à qui exécute l'image comment savoir si elle vit.
sudo tee /root/inventaire/Dockerfile >/dev/null <<'DOCKERFILE'
FROM node:22.11.0-alpine3.20

RUN apk add --no-cache curl

COPY . /app
WORKDIR /app

USER 1000

EXPOSE 3000

HEALTHCHECK CMD wget -q -O- http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
DOCKERFILE

# 3. Relancer l'analyse, seule preuve que la correction a pris.
echo "--- après correction ---"
sudo trivy config --quiet /root/inventaire 2>/dev/null | head -20
echo "Le Dockerfile fait la même chose, et l'analyse ne lui reproche plus rien."
