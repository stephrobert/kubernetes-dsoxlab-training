# Durcir un Pod avec un securityContext

## La situation

L'équipe sécurité a fixé la règle pour tout ce qui tourne dans le namespace
**`lab`** : pas de root, pas d'escalade de privilèges, une racine en lecture
seule, et aucune capability Linux. L'application à livrer est un serveur
web, image **`nginxinc/nginx-unprivileged:1.27-alpine`**, qui écoute sur le
port **8080**.

Ce serveur a besoin d'écrire quelque part pour démarrer. Avec une racine en
lecture seule, il ne le peut plus, et il le dira dans ses logs. À vous de
lui donner exactement les espaces d'écriture qu'il lui faut, et rien de
plus.

## Ce que vous devez obtenir

1. Un Pod **`hardened`** dans `lab`, avec cette image, en **`Running`**.

2. Le Pod tourne avec l'utilisateur **1000**, et refuse de tourner en root.
   Le conteneur n'autorise **aucune escalade de privilèges**, sa racine est
   en **lecture seule**, et il retire **toutes** les capabilities.

3. Le serveur **répond** en HTTP sur son port 8080.

4. De l'intérieur : le processus est bien l'utilisateur 1000, une écriture à
   la racine est refusée, et l'application a bien ses espaces d'écriture.

## Les repères utiles

Le `securityContext` existe à deux niveaux, et tous les champs ne sont pas
acceptés aux deux. Ce qui concerne l'utilisateur se déclare au niveau du Pod
ou du conteneur ; ce qui concerne le système de fichiers, l'escalade et les
capabilities se déclare au niveau du conteneur.

Un volume `emptyDir` est un espace d'écriture qui naît et meurt avec le Pod.
Il se monte où on veut, y compris par-dessus un répertoire de l'image.

## Comment vous saurez que c'est bon

Les tests lisent la définition du Pod, entrent dans le conteneur pour
vérifier l'utilisateur et tenter une écriture, et interrogent le serveur
depuis le nœud.

```bash
dsoxlab check ckad-security-context-hardened
```
