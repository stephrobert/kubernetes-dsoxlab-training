# Fermer un worker au réseau, sauf les flux dont Kubernetes a besoin

## La situation

Le second worker **`k8s-w2.lab`** n'a **aucun pare-feu** : chaque port en
écoute répond à tout le réseau. Vous ouvrez une session dessus depuis le
control plane avec `ssh k8s-w2.lab`, sous un compte qui a `sudo`.

Ce qui doit continuer à passer :

- **SSH (22)**, depuis le **poste d'administration** (l'adresse d'où arrivent
  vos sessions sur le control plane) et depuis le **control plane** lui-même ;
- le **kubelet (10250)**, depuis les **nœuds** du cluster et depuis le
  **réseau des Pods** (`metrics-server` le lit depuis un Pod) ;
- le plugin réseau **Calico** depuis les nœuds : **BGP (TCP 179)** et le
  tunnel **VXLAN (UDP 4789)**.

Tout le reste se ferme, y compris le port de santé de kube-proxy (10256).

## Ce que vous devez obtenir

1. Une chaîne d'entrée nftables en **politique `drop`** est chargée sur
   `k8s-w2.lab`. Un nœud qui n'est pas un poste d'administration, comme
   `k8s-w1.lab`, n'atteint plus ni SSH ni le port 10256.
2. Les flux du cluster passent : les nœuds atteignent le kubelet, le control
   plane atteint SSH, `kubectl logs` marche sur un Pod de `k8s-w2.lab`, et un
   Pod de `k8s-w1.lab` joint un Pod de `k8s-w2.lab` par un Service.
3. Les règles **survivent à un redémarrage** de `k8s-w2.lab`, sans effacer
   celles de kube-proxy et de Calico.

## Les repères

Relevez les valeurs avant d'écrire : `kubectl get nodes -o wide` pour les
adresses des nœuds, le `podSubnet` du ConfigMap `kubeadm-config`
(namespace `kube-system`) pour le réseau des Pods, `echo $SSH_CONNECTION` sur
le control plane pour l'adresse du poste.

kube-proxy et Calico écrivent leurs propres règles dans le noyau. Une table à
vous, sans **`flush ruleset`**, cohabite avec elles. Avant de charger une
politique `drop`, programmez son retrait automatique avec `systemd-run` : si
vous coupez votre propre session, elle tombera seule quelques minutes plus
tard.

Le service `nftables` d'Ubuntu recharge `/etc/nftables.conf` au démarrage.
Le fichier livré commence par `flush ruleset`. Et son arrêt (`systemctl stop`,
donc aussi `restart` sur un service actif) vide **tout** le jeu de règles :
sur un nœud Kubernetes, rechargez avec `nft -f` ou `systemctl reload
nftables`.

Une connexion déjà ouverte passe une règle `ct state established` : testez
toujours avec une connexion **neuve**.

## Comment vous saurez que ça marche

Les tests lisent le jeu de règles chargé, ouvrent des connexions neuves depuis
`k8s-w1.lab` et le control plane, font parler deux Pods à travers le nœud,
puis **redémarrent** `k8s-w2.lab` et vérifient que le pare-feu est revenu.

```bash
dsoxlab check cks-fermer-l-acces-reseau-au-noeud
```

Si vous vous êtes enfermé dehors et que le filet n'a pas joué :
`dsoxlab destroy --optional-hosts`, puis
`dsoxlab run cks-fermer-l-acces-reseau-au-noeud`.
