# Donner une seconde interface réseau à un Pod avec Multus

## La situation

Le cluster Cilium des hôtes `net-*` compte **trois nœuds** : `net-cp.lab`
(plan de contrôle), `net-w1.lab` et `net-w2.lab`. Cilium 1.20.5 remplace
kube-proxy et tourne avec son réglage par défaut **`cni.exclusive=true`**.

Une équipe stockage veut faire parler deux Pods par un **second réseau**,
distinct du réseau du cluster : un réseau macvlan sur l'interface `enp1s0` des
nœuds, en `192.168.100.0/24`. Le manifeste de **Multus v4.3.2** en mode thick
est prêt sur le plan de contrôle, son image épinglée par digest :
`/opt/multus/multus-daemonset-thick.yml`. Le namespace **`multus-demo`** est
vide. Les plugins CNI `macvlan` et `static` sont déjà sur chaque nœud.

Vous êtes sur `net-cp.lab`, avec `kubectl` et `helm` configurés.

## Ce que vous devez obtenir

1. Cilium **ne garde plus** la configuration CNI pour lui seul :
   `cni-exclusive` vaut `false`, et chaque agent Cilium est prêt.
2. **Multus v4.3.2** en mode thick tourne sur les trois nœuds, depuis l'image
   épinglée.
3. Une NetworkAttachmentDefinition **`reseau-stockage`** dans `multus-demo`
   décrit un réseau **macvlan** sur `enp1s0`, à adresses **static**.
4. Deux Pods de `multus-demo` ont chacun **deux interfaces** : **`client`** sur
   `net-w1.lab` avec `192.168.100.11/24`, **`serveur`** sur `net-w2.lab` avec
   `192.168.100.12/24`. `serveur` répond en HTTP sur le port **8080**.
5. Depuis `client`, `http://192.168.100.12:8080/` répond, et le même serveur
   répond toujours sur son adresse du cluster.

## La méthode, pas à pas

**D'abord, laisser Cilium partager la configuration CNI.** En mode exclusif,
l'agent Cilium renomme en `.cilium_bak` tout autre fichier de
`/etc/cni/net.d`, celui de Multus compris, sans un mot. `helm upgrade cilium
cilium/cilium --version 1.20.5 -n kube-system --reuse-values --set
cni.exclusive=false`, puis attendez les agents (`kubectl -n kube-system
rollout status ds/cilium`). Si Multus a été installé avant, son fichier reste
renommé : il faut redémarrer le Pod Multus du nœud pour qu'il le réécrive.

**Installer Multus.** `kubectl apply -f /opt/multus/multus-daemonset-thick.yml`
crée le DaemonSet `kube-multus-ds`, la CRD des NetworkAttachmentDefinition et
leurs rôles. Le manifeste amont du tag v4.3.2 pointe l'image mobile
`snapshot-thick` : cette copie est épinglée. Sur chaque nœud, Multus écrit
`00-multus.conf`, premier par ordre alphabétique, et confie le réseau du
cluster à Cilium.

**Décrire le second réseau.** Une `NetworkAttachmentDefinition` porte une
configuration CNI en JSON sous `spec.config` : `"type": "macvlan"`, `"master":
"enp1s0"`, `"mode": "bridge"`, et `"ipam": {"type": "static"}` pour que chaque
Pod apporte sa propre adresse.

**L'attacher aux Pods.** L'annotation `k8s.v1.cni.cncf.io/networks` nomme le
réseau et, en adressage static, l'adresse :
`'[{"name": "reseau-stockage", "ips": ["192.168.100.11/24"]}]'`. Placez chaque
Pod par `nodeName`. L'image
`busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e`
peut dormir pour le client, et servir une page pour le serveur avec
`httpd -f -p 8080 -h /tmp`.

**Vérifier.** `kubectl -n multus-demo exec client -- ip -4 addr` montre `eth0`
(Cilium) et `net1` (macvlan). L'annotation `k8s.v1.cni.cncf.io/network-status`
de chaque Pod liste les deux réseaux. Si un Pod reste en `ContainerCreating`,
`kubectl describe pod` donne l'erreur CNI, mot pour mot.

## Comment savoir que ça marche

Les tests lisent la configuration de Cilium, les Pods de Multus et l'image
qu'ils font tourner, la NetworkAttachmentDefinition et l'état réseau des deux
Pods. Puis ils demandent la page du serveur depuis le client, par le second
réseau et par le réseau du cluster.

```bash
dsoxlab check k8s-attacher-une-seconde-interface
```
