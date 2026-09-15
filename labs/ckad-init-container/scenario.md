# Attendre une dépendance avec un init container

## La situation

Dans le namespace **`lab`**, l'application **`app`** lit sa configuration au
démarrage sur un serveur interne, exposé par le Service **`config-svc`** sur
le port 80. Quand ce serveur n'est pas là, l'application démarre quand même,
sans configuration, et se comporte n'importe comment pendant des heures avant
que quelqu'un s'en aperçoive.

L'équipe veut que l'application **n'aille pas plus loin tant que
`config-svc` ne répond pas**. Le Service existe déjà, mais rien ne se tient
derrière lui pour l'instant : c'est la situation de départ, et c'est celle
qu'il faut savoir gérer.

## Ce que vous devez obtenir

1. Un Pod **`app`** dans `lab`, avec un init container nommé
   **`wait-for-config`** qui attend que `http://config-svc/` réponde, puis
   un conteneur principal nommé **`main`**, image `nginx:1.27-alpine`.

2. Tant que rien ne répond derrière `config-svc`, le Pod `app` reste en
   **`Init`** : constatez-le.

3. Un Pod **`config-server`** dans `lab`, image `nginx:1.27-alpine`, portant
   le label **`app=config`**, que le Service `config-svc` sélectionne.

4. Une fois `config-server` prêt, l'init container se termine et `app`
   passe en `Running` sans que vous ayez rien fait d'autre.

## Les repères utiles

Un init container s'exécute avant les conteneurs principaux, jusqu'au bout,
et le Pod attend qu'il réussisse. Une boucle `until` avec `wget` fait un
excellent gardien.

Un Service se résout dans le DNS dès qu'il existe, même sans endpoint :
attendre que le nom se résolve n'attend rien. Attendre une réponse HTTP,
oui.

## Comment vous saurez que c'est bon

Les tests lisent la définition du Pod `app`, les endpoints du Service, et
l'état de l'init container, terminé avec succès.

```bash
dsoxlab check ckad-init-container
```
