# Sortir un Pod de l'ImagePullBackOff

## La situation

Dans le namespace **`lab`**, le Pod **`broken-pod`** ne démarre plus depuis
la dernière mise à jour. L'équipe voulait passer sur la **variante Alpine de
nginx 1.27**, plus légère, et affirme que l'image existe sur le Docker Hub.
Pourtant `kubectl get pods` montre le Pod tantôt en `ErrImagePull`, tantôt en
`ImagePullBackOff`, jamais en `Running`.

Le nœud a accès à Internet, et d'autres images se téléchargent sans problème.
Le défaut est dans ce que le Pod demande, pas dans ce que le nœud peut faire.

## Ce que vous devez obtenir

1. Le Pod `broken-pod` **tourne**, conteneur prêt.

2. Son image est une image **nginx publique**, celle que l'équipe voulait,
   et elle a été réellement téléchargée sur le nœud.

3. Le serveur **répond en HTTP** : la page d'accueil de nginx est servie.

## Les repères utiles

`ImagePullBackOff` et `ErrImagePull` sont deux faces du même problème : le
runtime a essayé de télécharger l'image, a échoué, et le kubelet espace ses
tentatives. Le message **exact** du runtime, celui qui dit si c'est le
registre, le nom ou le tag qui cloche, n'est pas dans le statut du Pod : il est
dans ses events.

Un Pod nu accepte qu'on change son image en place ; le supprimer et le
recréer est aussi une réponse valable, tant que le résultat porte le même nom.

## Comment vous saurez que c'est bon

Les tests lisent l'état du Pod, l'image que le runtime a réellement tirée, et
ils interrogent le serveur depuis le nœud.

```bash
dsoxlab check cka-troubleshoot-imagepullbackoff
```
