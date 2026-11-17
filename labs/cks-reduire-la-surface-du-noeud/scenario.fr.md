# Retirer d'un worker ce qui écoute sans servir Kubernetes

## La situation

Le second worker **`k8s-w2.lab`** a été installé à partir d'un ancien modèle
de serveur. Vous ouvrez une session dessus depuis le control plane avec
`ssh k8s-w2.lab`, sous un compte qui a `sudo`.

Un balayage depuis le réseau a trouvé, en plus de ce qu'un worker utilise,
**trois ports ouverts** sur ce nœud. Aucun ne sert Kubernetes. Chaque service
qui écoute est une porte de plus pour un attaquant, et un paquet installé est
du code à corriger à chaque faille publiée.

Ce qu'un worker du cluster utilise réellement, sur toutes ses interfaces :
`sshd` (22), `bird`, le BGP de Calico (179), le kubelet (10250), kube-proxy
(10256), le tunnel VXLAN de Calico (UDP 4789), et le client DHCP (UDP 68, lié
à l'adresse du nœud). S'y ajoute `calico-typha` (5473) quand l'opérateur de
Calico en place une instance sur ce nœud.

## Ce que vous devez obtenir

1. Plus rien n'écoute sur les interfaces de `k8s-w2.lab` en dehors de la
   liste ci-dessus. Les ports **111**, **21** et **8000** refusent une
   connexion venue du control plane.
2. Le retrait est **durable** : les paquets superflus sont **purgés**, et ce
   qu'aucun paquet ne fournit est arrêté et **désactivé**. Rien ne doit
   revenir au prochain démarrage.
3. Le nœud reste un nœud Kubernetes : le kubelet, containerd et sshd tournent,
   le nœud est `Ready`, et un Pod placé dessus démarre.

## Les repères

`sudo ss -tulpn` liste ce qui écoute et nomme le processus. Une adresse
`127.0.0.1` ou `::1` n'est joignable que depuis la machine elle-même : elle
n'est pas dans la surface exposée.

Remontez de chaque processus à son unité systemd, puis à son paquet. Un
service peut être relancé par une **socket** systemd : arrêter le service ne
ferme alors pas le port. Un service qu'aucun paquet ne fournit ne partira pas
avec `apt`.

Gardez la commande de suppression pour la fin, une fois chaque port rattaché à
sa source : un paquet retiré par erreur, containerd ou le kubelet, sort le
nœud du cluster.

## Comment vous saurez que ça marche

Les tests lisent ce qui écoute sur `k8s-w2.lab`, essaient chaque port depuis
le control plane, lisent l'état des paquets et des unités, puis placent un Pod
sur le nœud.

```bash
dsoxlab check cks-reduire-la-surface-du-noeud
```
