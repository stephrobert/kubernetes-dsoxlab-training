#!/usr/bin/env bash
# Retire kubectl et toute trace de sa complétion, pour que l'apprenant
# l'installe lui-même :
#
#   - tout binaire kubectl que le PATH de l'utilisateur du lab ou celui de root
#     peut trouver, plus les emplacements habituels d'une installation à la main
#     (/usr/local/bin, ~/.local/bin, ~/bin) ;
#   - les fichiers de complétion kubectl, système et utilisateur ;
#   - dans les fichiers de démarrage de bash, les lignes qui chargent la
#     complétion de kubectl ou définissent l'alias k, laissées par un passage
#     précédent dans ce lab.
#
# Le cluster « lab » et ~/.kube/config ne sont pas touchés : l'apprenant s'en
# sert pour vérifier la connexion. Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"

# Les binaires que l'un ou l'autre PATH trouve, puis les emplacements connus.
# `type -aP` rend toutes les occurrences, pas seulement la première.
mapfile -t trouves < <(
  { type -aP kubectl || true
    sudo -u "$LAB_USER" -H bash -ic 'type -aP kubectl' < /dev/null 2>/dev/null || true
  } | sort -u
)
for binaire in "${trouves[@]}" /usr/local/bin/kubectl "${LAB_HOME}/.local/bin/kubectl" "${LAB_HOME}/bin/kubectl"; do
  if [ -n "$binaire" ]; then rm -f "$binaire"; fi
done

rm -f /etc/bash_completion.d/kubectl \
  /usr/share/bash-completion/completions/kubectl \
  "${LAB_HOME}/.local/share/bash-completion/completions/kubectl"

# Les lignes qui mentionnent kubectl ou définissent l'alias k. Le socle n'en
# écrit aucune : tout ce qui est retiré ici vient d'un passage dans ce lab.
for fichier in "${LAB_HOME}/.bashrc" "${LAB_HOME}/.bash_aliases" "${LAB_HOME}/.bash_profile" \
  "${LAB_HOME}/.profile" /etc/bash.bashrc; do
  if [ -f "$fichier" ]; then sed -i -e '/kubectl/d' -e '/^[[:space:]]*alias[[:space:]]\+k=/d' "$fichier"; fi
done

if command -v kubectl; then
  echo "kubectl est encore trouvé par le PATH de root" >&2
  exit 1
fi
if sudo -u "$LAB_USER" -H bash -ic 'command -v kubectl' < /dev/null 2>/dev/null; then
  echo "kubectl est encore trouvé par le PATH de ${LAB_USER}" >&2
  exit 1
fi
echo "kubectl retiré ; cluster prêt : $(kind get clusters 2>/dev/null | tr '\n' ' ')"
