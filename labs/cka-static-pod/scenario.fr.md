# Poser un Pod statique sur un worker, sans passer par l'API

## La situation

L'équipe réseau veut une page de statut servie depuis le worker
**`k8s-w1.lab`** lui-même, qui reste en ligne même quand l'API server est
injoignable. Un Deployment ne convient pas : sans API, rien ne le
replanifie. Ce qu'il faut, c'est un Pod que le **kubelet du worker gère
seul**, à partir d'un fichier posé sur le nœud.

Vous êtes sur le control plane. Comme à l'examen, `ssh k8s-w1.lab` vous
ouvre une session sur le worker.

## Ce que vous devez obtenir

1. Sur `k8s-w1.lab`, un manifeste de Pod déposé dans le **répertoire que le
   kubelet surveille**. Ce répertoire n'est pas à deviner : la configuration
   du kubelet le désigne.

2. Le Pod s'appelle **`static-web`**, tourne dans le namespace `default`,
   porte le label `role: static`, et son conteneur, nommé `web`, utilise
   l'image **`nginx:1.27-alpine`** et expose le **port 80**.

3. Le Pod apparaît dans l'API, en **`Running`**, sous le nom que le kubelet
   donne aux Pods miroirs : le nom du Pod suffixé du nom du nœud.

## Les repères utiles

Le kubelet ne crée pas ce Pod parce qu'on le lui a demandé par l'API : il
le crée parce qu'il a lu un fichier, et il publie ensuite dans l'API un
**Pod miroir** pour qu'on le voie, en lecture seule. Supprimer ce miroir ne
supprime rien : le kubelet le recrée. Seul le fichier compte.

Le chemin surveillé est un champ de `/var/lib/kubelet/config.yaml`, le
fichier que `kubeadm` a écrit en joignant le nœud. Un manifeste mal formé
n'apparaît nulle part dans l'API : c'est le journal du kubelet, sur le
worker, qui dit ce qu'il lui reproche.

## Comment vous saurez que c'est bon

Les tests lisent le fichier sur le worker, le Pod miroir dans l'API, et
demandent au runtime du worker s'il exécute vraiment le conteneur.

```bash
dsoxlab check cka-static-pod
```
