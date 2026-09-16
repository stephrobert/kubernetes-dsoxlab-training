#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NS=chaine-signature

# 1. La paire de clés. Deux précautions, et chacune vient d'un échec mesuré.
#
#    Le mot de passe vide passe par l'environnement : cosign le demande
#    autrement de façon interactive, et un script rejoué par le validateur n'a
#    personne pour répondre.
#
#    Tout le bloc passe par `sudo bash -c` parce que `cosign generate-key-pair`
#    écrit dans le répertoire COURANT, et que /root n'est pas accessible à
#    l'utilisateur du lab : un simple `cd /root` rend « Permission denied » et
#    fait échouer la solution entière.
sudo bash -c 'cd /root && rm -f cosign.key cosign.pub && COSIGN_PASSWORD="" cosign generate-key-pair'

# 2. La signature. Elle est poussée DANS le registre, à côté de l'image, sous
#    un tag dérivé du digest. C'est pour cela qu'un registre accessible en
#    écriture est indispensable.
sudo env COSIGN_PASSWORD="" cosign sign --key /root/cosign.key --yes \
  localhost:5000/appli/web:1.0

# 3. La clé publique, publiée dans le cluster pour que d'autres puissent
#    vérifier sans jamais toucher à la clé privée.
$K -n "$NS" delete configmap cosign-pub-key --ignore-not-found
$K -n "$NS" create configmap cosign-pub-key --from-file=cosign.pub=/root/cosign.pub

# 4. La preuve, dans les deux sens. Une vérification qui accepte tout ne
#    prouve rien : c'est l'image NON signée qui donne sa valeur au test.
echo -n "image signée   : "
sudo cosign verify --key /root/cosign.pub localhost:5000/appli/web:1.0 >/dev/null 2>&1 \
  && echo "acceptée" || echo "REFUSÉE, anormal"
echo -n "image non signée : "
sudo cosign verify --key /root/cosign.pub localhost:5000/appli/outil:1.0 >/dev/null 2>&1 \
  && echo "ACCEPTÉE, anormal" || echo "refusée"
echo "La chaîne de signature tient : une clé, une image acceptée, une refusée."
