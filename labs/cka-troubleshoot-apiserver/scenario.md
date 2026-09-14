# Remettre l'API server en service

## La situation

Depuis quelques minutes, `kubectl` ne répond plus sur le cluster :
`connection refused` sur le port 6443 du control plane. Rien n'a été déployé.
Un collègue reconnaît avoir « juste ajusté un flag de l'API server » pour un
test de sécurité, juste avant de partir.

Le control plane **`k8s-cp.lab`** est accessible : vous y êtes. L'API, elle,
ne l'est plus, et tout ce que `kubectl` sait faire est hors service avec elle.

## Ce que vous devez obtenir

1. L'API server **répond** : `kubectl get nodes` fonctionne, et `/healthz`
   rend `ok`.

2. Le Pod statique **`kube-apiserver-k8s-cp.lab`** tourne dans `kube-system`,
   sans redémarrer en boucle.

3. Le manifeste de l'API server ne porte plus le flag fautif, et il autorise
   toujours **`Node,RBAC`** : un API server qui démarre en acceptant tout le
   monde n'est pas réparé, il est ouvert.

## Les repères utiles

Sur un cluster kubeadm, l'API server n'est pas un service systemd : c'est un
**Pod statique**, dont le kubelet lit la définition dans un répertoire de
manifestes et qu'il redéploie dès que le fichier change. Pas besoin de
`kubectl` pour le relancer : il suffit de corriger le fichier.

Sans API, `kubectl` est aveugle, mais le nœud ne l'est pas : le runtime de
conteneurs voit les conteneurs, morts ou vivants, et garde leurs journaux ;
le kubelet raconte dans `journalctl` ce qu'il essaie de démarrer.

## Comment vous saurez que c'est bon

Les tests interrogent l'API, lisent l'état du Pod statique, et relisent le
manifeste sur le nœud pour vérifier que l'autorisation y est toujours.

```bash
dsoxlab check cka-troubleshoot-apiserver
```
