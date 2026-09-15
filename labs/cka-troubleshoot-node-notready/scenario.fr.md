# Ramener un nœud NotReady dans le cluster

## La situation

Le worker **`k8s-w1.lab`** est passé **`NotReady`** ce matin, et personne ne
sait pourquoi. Le control plane, lui, va bien.

L'application **`web-app`**, dans le namespace **`production`**, doit tourner
en trois replicas. Elle est **réservée à ce worker** par un `nodeSelector`,
pour des raisons de licence : elle n'a nulle part ailleurs où aller. Depuis
ce matin, elle est dégradée.

Vous êtes sur le control plane. Comme à l'examen, `ssh k8s-w1.lab` vous ouvre
une session sur le worker.

## Ce que vous devez obtenir

1. Le nœud `k8s-w1.lab` est **`Ready`**.

2. L'agent du nœud **tourne**, et il **survivra à un redémarrage** de la
   machine : réparer pour une heure ne compte pas.

3. Le Deployment `web-app` a ses **trois replicas disponibles**, sur
   `k8s-w1.lab`.

## Les repères utiles

Un nœud `NotReady` est un nœud dont l'agent ne donne plus de nouvelles au
control plane. `kubectl describe node` le dit dans ses conditions, avec
l'heure du dernier signe de vie. Le reste ne se lit pas depuis le control
plane : il faut aller sur le nœud, et y interroger systemd.

Un service peut être arrêté de deux façons, et l'une des deux ne se voit pas
dans `systemctl status`.

## Comment vous saurez que c'est bon

Les tests lisent l'état du nœud depuis l'API, l'état du service sur le worker
lui-même, et l'état du Deployment.

```bash
dsoxlab check cka-troubleshoot-node-notready
```
