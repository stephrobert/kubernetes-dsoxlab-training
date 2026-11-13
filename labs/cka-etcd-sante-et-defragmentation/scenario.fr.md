# Contrôler la santé d'etcd et défragmenter sa base

## La situation

etcd garde tout l'état du cluster. Un etcd en mauvaise santé, ou une base qui
s'approche de son quota, et l'API server cesse d'écrire. Une équipe a créé puis
supprimé beaucoup d'objets : la base a grossi, et elle n'a pas rapetissé.

Vous êtes sur **`k8s-cp.lab`**, le plan de contrôle du cluster kubeadm, avec
`kubectl` configuré. etcd y tourne en Pod statique, **`etcd-k8s-cp.lab`**, et
son image contient `etcdctl`. Ses certificats sont sous
`/etc/kubernetes/pki/etcd/`.

## Ce que vous devez obtenir

1. Dans **`~/etcd/reponses.yaml`** : l'**identifiant du membre** etcd (en
   hexadécimal), son **point d'accès client**, et s'il est en **bonne santé**.
2. Dans le même fichier : le **quota d'espace** que cet etcd applique, en octets.
3. La base etcd est **défragmentée** : elle a rendu la place que les objets
   supprimés occupaient encore.

## Les repères utiles

- `etcdctl` exige les certificats TLS : `--cacert`, `--cert`, `--key`. Les
  options du Pod statique, dans `/etc/kubernetes/manifests/etcd.yaml`, disent
  lesquels employer.
- `etcdctl member list`, `endpoint health` et `endpoint status` répondent aux
  deux premières questions. `-w table` ou `-w json` changent la sortie.
- Un etcd sans option `--quota-backend-bytes` applique la valeur par défaut, que
  la leçon donne.
- Le **compactage** supprime les anciennes révisions et libère de la place
  **dans** le fichier. Seule la **défragmentation** rend cette place au disque.
  `endpoint status` montre la taille de la base avant et après.

## Comment vous saurez que c'est bon

Les tests interrogent etcd avec ses certificats et comparent vos réponses à ce
qu'il dit de lui-même, puis mesurent la taille de la base par rapport à celle
que le setup a relevée.

```bash
dsoxlab check cka-etcd-sante-et-defragmentation
```
