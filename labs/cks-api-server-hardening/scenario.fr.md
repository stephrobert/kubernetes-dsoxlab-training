# Fermer le profileur de l'API server, sans fermer l'API

## La situation

Le cluster sort d'une installation `kubeadm` par défaut. Comme tous ceux qui
en sortent, son API server expose `/debug/pprof/`, le profileur du langage Go :
qui l'atteint apprend la consommation mémoire, le nombre de goroutines et la
charge du composant le plus sensible du cluster.

Personne ne s'en sert, et il est ouvert.

## Ce que vous devez obtenir

1. Le profileur **ne répond plus**.

2. Deux autres réglages de durcissement sont posés sur l'API server : la
   **révocation effective des jetons de compte de service**, et un **plancher
   de version TLS** à 1.2.

3. **Le cluster fonctionne toujours.** `kubectl get nodes` répond, et le Pod
   statique de l'API server est revenu en `Running`.

4. Vous n'ajoutez **pas** `--anonymous-auth=false`. Ce flag n'est pas demandé,
   et il casse ce cluster : les raisons sont dans les indices si vous voulez
   savoir pourquoi avant de l'essayer.

## Les repères utiles

L'API server est un **Pod statique**. Sa définition est un fichier du nœud,
sous `/etc/kubernetes/manifests/`, et le kubelet le surveille : dès que le
fichier change, il redéploie le Pod. L'API disparaît alors une dizaine de
secondes, ce qui est normal.

Un flag refusé au démarrage fait sortir le conteneur immédiatement, et le
kubelet le relance en boucle. Pendant ce temps `kubectl` ne répond plus, ce
qui rend le diagnostic inconfortable : `sudo crictl ps -a | grep
kube-apiserver` puis `sudo crictl logs <id>` donnent la ligne exacte, sans
passer par l'API.

Le manifeste d'origine est sauvegardé par le setup sous `/var/backups`. En cas
de blocage, le recopier à sa place rend le cluster.

## Comment vous saurez que c'est bon

Le dernier test exerce **les deux moitiés** de l'exigence : `/debug/pprof/`
doit rendre une erreur, **et** `/version` doit répondre normalement. Un API
server à l'arrêt ferme le profileur aussi sûrement qu'un flag bien posé, et
c'est le contresens le plus fréquent du durcissement.

```bash
dsoxlab check cks-api-server-hardening
```
