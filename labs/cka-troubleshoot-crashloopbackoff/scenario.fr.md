# Sortir un Deployment du CrashLoopBackOff

## La situation

Dans le namespace **`production`**, le Deployment **`api-server`** doit
tourner en deux replicas. Depuis la dernière livraison, ses Pods
**redémarrent en boucle** : `kubectl get pods` les montre en
`CrashLoopBackOff`, avec un compteur de redémarrages qui grimpe.

L'équipe jure que l'image n'a pas changé. Elle a déposé la configuration de
l'application dans le namespace, et dit que « tout est là ». La charte de
l'équipe est simple : une application lit sa configuration à l'endroit que
lui indique la variable d'environnement **`APP_CONFIG_PATH`**, et cet endroit
est **`/etc/config`**.

## Ce que vous devez obtenir

1. Le Deployment `api-server` a **deux replicas disponibles**.

2. Plus aucun Pod de `api-server` ne redémarre en boucle.

3. Dans les Pods, `APP_CONFIG_PATH` vaut `/etc/config`, et l'application y
   trouve réellement son fichier `app.conf`.

4. L'application **répond** : elle sert son `app.conf` sur son port.

La correction se fait **sur le Deployment**, pas sur les Pods : un Pod
corrigé à la main serait remplacé à la prochaine occasion.

## Les repères utiles

`CrashLoopBackOff` n'est pas une cause, c'est une conséquence : le conteneur
démarre, s'arrête aussitôt, et le kubelet espace ses redémarrages. Le pourquoi
est dans ce que le processus a écrit avant de mourir, et dans ce que le
Deployment lui donne, ou ne lui donne pas.

Regardez ce que le namespace contient d'autre que le Deployment.

## Comment vous saurez que c'est bon

Les tests lisent l'état du Deployment et de ses Pods, puis ils entrent dans un
Pod pour lire le fichier de configuration et interroger l'application.

```bash
dsoxlab check cka-troubleshoot-crashloopbackoff
```
