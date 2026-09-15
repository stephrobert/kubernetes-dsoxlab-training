# Réparer un kubelet qui refuse de démarrer

## La situation

Hier soir, un collègue a « juste ajusté le DNS » sur le worker
**`k8s-w1.lab`**. Ce matin, le nœud est **`NotReady`**, et `systemctl start
kubelet` ne change rien : le service repart, puis s'arrête aussitôt, encore
et encore.

L'application **`web-app`**, dans le namespace **`production`**, est réservée
à ce worker par un `nodeSelector` et doit tourner en trois replicas. Elle est
dégradée depuis la nuit.

Vous êtes sur le control plane. Comme à l'examen, `ssh k8s-w1.lab` vous ouvre
une session sur le worker.

## Ce que vous devez obtenir

1. Le nœud `k8s-w1.lab` est **`Ready`**.

2. Le kubelet **tourne**, avec une configuration **valide** : l'adresse
   légitime du DNS du cluster, celle du Service `kube-dns`, doit y rester.
   Réparer en supprimant toute la configuration n'est pas réparer.

3. Le Deployment `web-app` a ses **trois replicas disponibles**, sur
   `k8s-w1.lab`.

## Les repères utiles

Un service qui s'arrête aussitôt lancé dit pourquoi dans le journal, et le
kubelet est précis sur ce point : il nomme le fichier qu'il ne parvient pas à
lire, et la ligne. Sur un cluster kubeadm, il lit sa configuration dans un
fichier YAML sous `/var/lib/kubelet`, écrit par `kubeadm` au moment de la
jointure du nœud.

Ce que `kubeadm` a écrit est correct ; ce qui a été ajouté après ne l'est pas,
ni dans sa forme, ni dans son contenu.

## Comment vous saurez que c'est bon

Les tests lisent l'état du nœud depuis l'API, l'état du service et le fichier
de configuration sur le worker lui-même, et l'état du Deployment.

```bash
dsoxlab check cka-troubleshoot-kubelet
```
