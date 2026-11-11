# Isoler une application dans un namespace

## La situation

Le cluster kind **`boutique`** tourne sur la machine, et votre `kubectl` le vise
déjà. Les namespaces **`equipe-api`** et **`equipe-front`** n'existent pas
encore. Le relevé **`~/namespaces/releve.txt`** attend ce que vous observerez.

## Ce que vous devez obtenir

1. L'application **`api`** (un Deployment nginx sur
   `nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb`)
   et son Service **`api`** sur le port 80 sont dans le namespace
   **`equipe-api`**, et **rien** ne s'appelle `api` dans `default`.

2. Un Pod **`client`** (busybox 1.38.0, qui dort) tourne dans
   **`equipe-front`**. Depuis lui, `api` répond par son **nom qualifié du
   namespace**, et **`reponse-nom-qualifie`** contient ce qu'il répond (au moins
   la ligne de titre).

3. Depuis ce même Pod, le **nom court** `api` échoue, et **`nom-court`** dit ce
   que vous avez constaté.

## Les repères utiles

Un namespace sépare les noms : deux objets peuvent porter le même nom dans deux
namespaces. Il ne sépare pas le réseau : un Pod de n'importe quel namespace peut
joindre un Service, pourvu qu'il le nomme bien. Sans `-n`, chaque commande vise
le namespace par défaut de votre contexte.

La leçon Services l'a montré : le nom court d'un Service ne se résout que dans
le namespace du client. Pour viser un autre namespace, on ajoute son nom après
celui du Service. Une requête qui ne doit pas aboutir se lance avec un délai
court, pour ne pas attendre.

## Comment vous saurez que c'est bon

Les tests lisent les objets des deux namespaces et votre relevé, puis rejouent
les deux requêtes depuis le Pod client.

```bash
dsoxlab check k8s-isoler-par-namespace
```
