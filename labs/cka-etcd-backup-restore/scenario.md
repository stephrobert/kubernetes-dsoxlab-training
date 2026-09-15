# Sauvegarder etcd, puis restaurer le cluster depuis un instantané

## La situation

Ce matin, le namespace **`important-data`** n'existe plus. Il portait un
ConfigMap **`mission-critical`** dont l'équipe a besoin aujourd'hui, et
personne ne sait ce qui s'est passé.

Une sauvegarde d'etcd a été prise hier soir, avant l'incident :
**`/opt/backup/etcd-snapshot-previous.db`**. Le cluster est un kubeadm à un
control plane, **`k8s-cp.lab`**, sur lequel vous êtes connecté avec les
droits `sudo`. Les outils `etcdctl` et `etcdutl` sont installés, dans la
version de l'etcd qui tourne.

## Ce que vous devez obtenir

1. **Avant toute chose**, une sauvegarde fraîche de l'état courant dans
   **`/opt/backup/etcd-snapshot.db`**, vérifiée. On ne restaure jamais sans
   avoir sauvegardé ce qu'on s'apprête à écraser.

2. Le cluster **restauré depuis la sauvegarde d'hier soir**, dans un
   répertoire de données neuf, et etcd qui tourne dessus. Le namespace
   `important-data` et son ConfigMap sont de retour, tels qu'ils étaient.

3. Un cluster **sain** après l'opération : l'API répond, les deux nœuds sont
   `Ready`, et ce que l'API server avait en cache avant la restauration ne
   traîne plus.

## Les repères utiles

Sur ce cluster, etcd est un Pod statique : son manifeste dans
`/etc/kubernetes/manifests` dit où sont ses certificats, son répertoire de
données, et sous quel nom il se connaît. Le kubelet relance ce Pod dès que
le manifeste change, et l'arrête dès que le manifeste disparaît du
répertoire. Arrêter le kubelet, lui, n'arrête aucun conteneur.

Depuis etcd 3.6, `etcdctl` ne sait plus que prendre un instantané ; le
vérifier et le restaurer sont le travail de `etcdutl`, hors ligne, dans un
répertoire qui n'existe pas encore. Le nom du membre, le cluster initial et
l'URL de pair qu'on lui donne doivent être ceux du manifeste.

L'API server garde en mémoire ce qu'il a lu dans etcd. Restaurer sous ses
pieds sans le relancer laisse ce cache en désaccord avec la base.

## Comment vous saurez que c'est bon

Les tests lisent l'instantané frais, la date du répertoire de données que
l'etcd en marche utilise, les UID des objets revenus, et cherchent un objet
créé après la sauvegarde d'hier soir, qui ne doit plus exister.

```bash
dsoxlab check cka-etcd-backup-restore
```
