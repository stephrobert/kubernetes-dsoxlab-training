# Fusionner un kubeconfig et changer de contexte

## La situation

Votre `kubectl` vise le cluster kind **`boutique`** par le contexte
**`kind-boutique`**, écrit dans `~/.kube/config`, un fichier aujourd'hui
lisible par tous les comptes de la machine. Une collègue vous a envoyé
l'accès à un second cluster : le fichier
**`~/Downloads/kubeconfig-recette.yaml`**, posé là comme un téléchargement,
lisible par tous. Son contexte s'appelle `kind-recette`.

## Ce que vous devez obtenir

1. Le fichier reçu est **rangé** dans **`~/.kube/configs/recette.yaml`**,
   lisible par vous seul, et il **n'est plus** dans `~/Downloads`.

2. `~/.kube/config` porte un contexte **`recette`** qui vise le cluster reçu,
   **à côté** de `kind-boutique`, qui doit survivre à l'opération.

3. Le **contexte actif** est `recette`.

4. Le **namespace par défaut** du contexte `recette` est **`kube-system`**.

5. `~/.kube/config` n'est **lisible que par vous**.

## Les repères utiles

Lisez toujours un kubeconfig reçu avant de vous en servir : à quelle adresse il
envoie vos commandes, sous quel nom de contexte, avec quelle identité. La
variable `KUBECONFIG`, posée devant une commande, ne vaut que pour elle.

Fusionner n'est pas copier. Copier le fichier reçu par-dessus le vôtre vous
ferait perdre `kind-boutique`. La leçon montre comment lister les deux fichiers
dans `KUBECONFIG` et en tirer un seul fichier aplati, après une sauvegarde,
sans oublier de défaire `KUBECONFIG` ensuite.

Un fichier écrit par une redirection prend les droits par défaut : vérifiez-les
avec `ls -l`, et restreignez-les. `kubectl config` sait renommer un contexte,
basculer, et régler le namespace par défaut du contexte courant ; il ne vérifie
pas que le namespace existe, relisez donc ce que vous avez écrit.

## Comment vous saurez que c'est bon

Les tests lisent vos fichiers kubeconfig et leurs droits.

```bash
dsoxlab check k8s-changer-de-contexte
```
