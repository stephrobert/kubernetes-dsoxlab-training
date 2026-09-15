# Rétablir la résolution DNS du cluster

## La situation

Une équipe vous appelle : son application ne répond plus. Elle tourne dans le
namespace **`app`** et n'a rien de compliqué : un Pod **`web`** qui sert une
page, un Service **`web-svc`** qui l'expose, et un Pod **`client`** qui
l'interroge par son nom, `web-svc.app.svc.cluster.local`.

Personne n'a touché à l'application. Le Pod `web` tourne, le Service existe,
et pourtant le client ne joint plus rien : le nom ne se résout plus. Ce n'est
pas l'application qui est cassée, c'est **quelque chose dans le cluster**.

## Ce que vous devez obtenir

1. Depuis le Pod `client`, le nom `web-svc.app.svc.cluster.local` se résout
   à nouveau.

2. Le Pod `client` joint `web-svc` en HTTP par ce nom.

3. Le composant qui résout les noms dans le cluster est **de nouveau en
   service**, dans l'état où un cluster kubeadm le pose. Une rustine dans
   le Pod `client` ne compte pas : c'est le cluster qu'on vous demande de
   réparer.

## Les repères utiles

La résolution de noms dans Kubernetes n'est pas assurée par les Pods
eux-mêmes : chaque Pod interroge un Service du namespace **`kube-system`**,
dont l'adresse est écrite dans son `/etc/resolv.conf`. Ce Service, comme
tous les autres, ne répond que si des Pods se tiennent derrière lui.

Commencez par constater la panne depuis le Pod `client`, puis remontez : le
Service, ses endpoints, et ce qui devrait les fournir.

## Comment vous saurez que c'est bon

Les tests lisent l'état du **cluster**, pas les commandes que vous avez
tapées : ils regardent le composant DNS, puis ils tentent réellement une
résolution et une requête HTTP depuis le Pod `client`.

```bash
dsoxlab check cka-troubleshoot-dns
```
