# Installer un cluster kubeadm, y joindre un nœud et rendre le plan de contrôle hautement disponible

## La situation

Deux chantiers vous attendent.

Sur le cluster kubeadm, le worker **`k8s-w1.lab`** a été retiré du cluster et
réinitialisé : ce n'est plus un nœud, et sa préparation a été défaite.
L'équipe le veut de retour en service, proprement : une machine jointe à la
hâte tombe à son premier redémarrage.

En parallèle, l'équipe veut voir un plan de contrôle **hautement disponible**
tenir la perte d'un de ses membres. Faute de trois machines libres, elle vous
confie l'hôte **`k8s-kind.lab`**, où Docker et kind sont installés. Vous y
montez un cluster kind nommé **`ha`**, avec l'image de nœud du catalogue :

```text
kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
```

Vous êtes sur **`k8s-cp.lab`**, le plan de contrôle du cluster kubeadm, avec
`kubectl` configuré et les droits `sudo`. `ssh k8s-w1.lab` et
`ssh k8s-kind.lab` ouvrent une session sur les deux autres machines, où vous
avez aussi `sudo`. Aucune procédure n'est donnée : le module vous a appris ce
qu'il faut.

## Ce que vous devez obtenir

1. **`k8s-w1.lab`** est un nœud du cluster kubeadm, **Ready**, et son
   **kubelet** annonce une version **1.37**.
2. Le **swap** est **coupé** sur le worker, et **rien ne le rallumera** au
   prochain démarrage.
3. **containerd** tourne sur le worker avec le **pilote de cgroup systemd**.
4. Un Pod nommé **`temoin`**, dans le namespace **`installation`**, est
   **forcé sur `k8s-w1.lab`** par le champ `nodeName` de sa spec, et il tourne.
5. Le cluster **`ha`** compte **trois nœuds control-plane**, tous **Ready**,
   lus par l'**adresse du répartiteur** qui se tient devant leurs API servers.
6. **etcd** y compte **trois membres** votants et **sains**.
7. L'**API** de `ha` répond toujours, **par l'adresse du répartiteur**, quand
   un de ses plans de contrôle est **arrêté**.

## Comment vous serez noté

Sept états, à poids égal. Le seuil est de **70 sur 100**, et les états **1 et
7** sont **bloquants** : le worker joint, et l'API qui survit à la perte d'un
plan de contrôle. Réussir les autres ne compense pas l'un d'eux manqué.

Pour l'état 7, le correcteur **arrête lui-même** un plan de contrôle de `ha`
(il gèle son conteneur), interroge `/readyz` par le répartiteur, puis le
**remet en marche**. Chaque check agit donc sur le cluster `ha` pendant une
bonne minute. Le retour se limite à la liste des critères non satisfaits, par leur libellé, et à la note : aucun message ne dit pourquoi.

```bash
dsoxlab check  k8s-challenge-installer-un-cluster
dsoxlab submit k8s-challenge-installer-un-cluster
```
