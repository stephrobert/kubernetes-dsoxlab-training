# Joindre un worker à un cluster kubeadm

## La situation

Le worker **`k8s-w1.lab`** a été retiré du cluster et réinitialisé : il n'est
plus un nœud, et sa préparation a été défaite. L'équipe veut le remettre en
service, proprement : une machine jointe à la hâte retombe au premier
redémarrage.

Vous êtes sur **`k8s-cp.lab`**, le plan de contrôle, avec `kubectl` configuré et
les droits `sudo`. Le worker se joint par `ssh k8s-w1.lab`, où vous avez aussi
`sudo`.

## Ce que vous devez obtenir

1. **`k8s-w1.lab`** est un nœud du cluster, **Ready**.
2. Son **kubelet** annonce la **même version** que l'API server.
3. Le **swap** est **coupé** sur le worker, et **rien ne le rallumera** au
   prochain démarrage.
4. **containerd** tourne avec le **pilote de cgroup systemd**, celui du kubelet.
5. **kubeadm**, **kubelet** et **kubectl** sont **figés** sur le worker.
6. Un **Pod** du namespace **`jonction`** tourne **sur `k8s-w1.lab`**.

## Les repères utiles

- La jonction se fait **depuis le worker**, avec une commande que **le plan de
  contrôle fabrique** : elle porte un jeton à durée de vie limitée et
  l'empreinte de la CA du cluster.
- Le kubelet **refuse de démarrer** tant que du swap est actif. `swapon --show`
  dit ce qui l'est, `/etc/fstab` ce qui le sera au démarrage.
- La configuration de containerd vit dans `/etc/containerd/config.toml`, et il
  ne la relit **qu'à son redémarrage**.
- `apt-mark` fige et dégèle un paquet.
- Un Pod se place sur un nœud précis par le champ `nodeName` de sa spec, qui
  court-circuite le scheduler.
- Une jonction qui échoue se lit dans la sortie de `kubeadm join` et dans le
  journal du kubelet : `journalctl -u kubelet`.
