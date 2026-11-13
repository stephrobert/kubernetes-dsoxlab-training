# Lire les interfaces CRI, CNI et CSI d'un nœud

## La situation

Un nœud qui reste `NotReady`, un Pod qui ne démarre pas, un volume qui ne se
monte pas : chacune de ces pannes vit derrière l'une des trois interfaces que
Kubernetes délègue à un composant externe. Avant de dépanner, il faut savoir
**où regarder** sur un nœud.

Vous êtes sur **`k8s-cp.lab`**, un nœud du cluster kubeadm, avec `kubectl`
configuré. Le fichier **`~/interfaces/reponses.yaml`** attend ce que vous
allez lire.

## Ce que vous devez obtenir

Dans `~/interfaces/reponses.yaml` :

1. **`runtime_socket`** : le socket du runtime de conteneurs que le **kubelet**
   emploie, tel qu'il le déclare.
2. **`runtime`** : le runtime et sa version, tels que le nœud les **annonce à
   l'API** (`nom://version`).
3. **`cni_config`** et **`cni_plugin`** : le fichier de configuration CNI **en
   vigueur** dans `/etc/cni/net.d`, et le type de son **premier plugin**.
4. **`csi_drivers`** : la liste exacte des **pilotes CSI** enregistrés dans le
   cluster.

## Les repères utiles

- Le kubelet décrit sa configuration dans `/var/lib/kubelet/config.yaml`, et
  kubeadm lui passe ses options dans `/var/lib/kubelet/kubeadm-flags.env`.
- Ce que le nœud annonce à l'API se lit dans `kubectl get node -o wide` ou dans
  son `status.nodeInfo`.
- Quand plusieurs fichiers sont présents dans `/etc/cni/net.d`, le runtime
  prend le **premier par ordre alphabétique**.
- Les pilotes CSI s'enregistrent comme des objets `CSIDriver`.

## Comment vous saurez que c'est bon

Chaque test relit la valeur réelle sur le nœud au moment du check et la compare
à votre réponse. Une valeur recopiée d'une documentation ne passe pas : seule
compte celle de ce cluster.

```bash
dsoxlab check k8s-lire-les-interfaces-d-un-noeud
```
