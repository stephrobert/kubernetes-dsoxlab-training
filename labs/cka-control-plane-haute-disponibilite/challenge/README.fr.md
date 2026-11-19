# Challenge : Monter un plan de contrôle kubeadm à trois nœuds derrière un répartiteur, et en perdre un

## La situation

L'équipe veut un cluster qui survit à la perte d'une machine du plan de
contrôle. On vous a préparé quatre machines :

- **`ha-cp1`**, **`ha-cp2`** et **`ha-cp3`** : prêtes pour kubeadm (swap
  coupé, containerd, kubelet, kubeadm et kubectl 1.37), **sans cluster** ;
- **`ha-lb`** : un répartiteur **HAProxy** qui écoute sur
  **`ha-lb.lab:6443`** et renvoie vers le port 6443 des trois nœuds.

Vous êtes sur `ha-cp1`. Depuis là, `ssh ha-cp2` et `ssh ha-cp3` ouvrent une
session sans mot de passe, et `sudo` est disponible partout.

## Ce que vous devez obtenir

1. Le cluster a pour point d'accès le **répartiteur**, `ha-lb.lab:6443`.
2. **`ha-cp1`, `ha-cp2` et `ha-cp3`** sont tous trois des **plans de
   contrôle** `Ready`, en 1.37.
3. **etcd compte trois membres votants**, tous sains (etcd empilé, un membre
   par plan de contrôle).
4. Le cluster **survit à la perte d'un plan de contrôle** : `ha-cp2` arrêté,
   on écrit encore dans le cluster par le répartiteur.

## Les repères

Le point d'accès se fixe à l'initialisation (`--control-plane-endpoint`) et
**ne se modifie plus ensuite**. `--upload-certs` dépose les certificats du
cluster dans un Secret, d'où les autres plans de contrôle les récupèrent avec
leur clé de certificats (valable deux heures).

Un nœud joint sans `--control-plane` devient un worker. Un nœud reste
`NotReady` tant qu'aucun CNI n'est posé : la leçon utilise Flannel, avec le
réseau de Pods `10.244.0.0/16`.

`etcdctl` n'est pas installé sur un nœud kubeadm : il se lance dans le Pod
etcd, avec les certificats de `/etc/kubernetes/pki/etcd/`.

Si l'initialisation part mal, `sudo kubeadm reset -f` remet un nœud à zéro.

## Comment vous saurez que ça marche

Les tests lisent la configuration de kubeadm, les nœuds et les membres
d'etcd. Puis ils arrêtent `ha-cp2` (son kubelet et ses conteneurs), écrivent
dans le cluster par le répartiteur, relancent `ha-cp2` et attendent que son
membre etcd revienne.

```bash
dsoxlab check cka-control-plane-haute-disponibilite
```
