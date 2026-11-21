# Challenge : Durcir un nœud worker et l'accès à l'API server, sans casser le cluster

## 📍 La situation

Le second worker **`k8s-w2.lab`** vient de rejoindre le cluster. Il a été
installé depuis un ancien modèle de serveur, qui y a laissé beaucoup de choses
dont Kubernetes n'a pas besoin. Un prestataire y avait aussi un accès, et son
contrat est terminé.

Côté plan de contrôle, l'API server répond encore aux clients sans
identifiant, et quelqu'un a donné à ces clients le droit de lire le cluster.

Vous êtes sur le control plane, avec `kubectl` et `sudo`. Vous ouvrez une
session sur le nœud avec `ssh k8s-w2.lab`. Aucune procédure n'est donnée : le
module vous a appris ce qu'il faut.

Ce qui doit continuer à fonctionner pendant et après votre travail :

- **SSH (22)** vers `k8s-w2.lab`, depuis le **poste d'administration**
  (l'adresse d'où arrivent vos sessions sur le control plane) et depuis le
  **control plane** ;
- le **kubelet (10250)** du nœud, depuis les nœuds du cluster et depuis le
  réseau des Pods ;
- le plugin réseau **Calico** entre les nœuds : **BGP (TCP 179)** et
  **VXLAN (UDP 4789)** ;
- les **sondes de santé** de l'API server et la **jonction d'un nouveau nœud**
  par `kubeadm join`.

## 🎯 Ce que vous devez obtenir

1. `k8s-w2.lab` ne fait plus tourner ce dont il n'a pas besoin : le serveur
   web **apache2** est **purgé**, et le **relevé d'inventaire** qui écoute sur
   le port **9090** est arrêté et désactivé.

2. Seuls les membres du groupe **`ops-noeuds`** ouvrent une session SSH sur
   `k8s-w2.lab`. Ce groupe contient `ansible` et `student`. sshd n'accepte que
   les **clés**, et **root** ne se connecte pas.

3. Le compte **`prestataire`** reste sur le nœud, ses fichiers sont gardés
   pour l'audit, mais il n'a **plus aucun droit sudo**.

4. Le **kubelet** de `k8s-w2.lab` répond **401** à un client anonyme,
   **délègue** ses décisions d'autorisation à l'API server, et son **port en
   lecture seule** 10255 est fermé.

5. Une chaîne d'entrée nftables en **politique `drop`** ferme `k8s-w2.lab`.
   Un nœud qui n'est pas un poste d'administration, comme `k8s-w1.lab`,
   n'atteint plus SSH ni le port 10256. Les flux de la liste ci-dessus passent.

6. Un client anonyme n'atteint plus que les chemins de santé (`/livez`,
   `/readyz`, `/healthz`) et ce dont `kubeadm join` a besoin. Partout ailleurs,
   l'API server lui répond **401**. La configuration d'authentification vit
   dans **`/etc/kubernetes/authn-config.yaml`**. Aucune liaison RBAC ne donne de
   droits aux anonymes en dehors de celles que l'API server et kubeadm posent
   eux-mêmes. **Exigence bloquante.**

7. Tout ce qui précède **survit à un redémarrage** de `k8s-w2.lab`, et le
   nœud revient **Ready**. **Exigence bloquante.**

## ✅ Comment vous saurez que c'est bon

Les tests lisent les ports réellement en écoute, ouvrent de vraies sessions
SSH, demandent à sudo les droits du prestataire, interrogent le kubelet et
l'API server sans identifiant puis avec un compte sans droit, et ouvrent des
connexions neuves depuis `k8s-w1.lab` et depuis le control plane. Ils placent
aussi un Pod sur `k8s-w2.lab` et le joignent par un Service depuis
`k8s-w1.lab`. Le dernier test **redémarre `k8s-w2.lab`** et refait ses
contrôles.

Sept exigences, à poids égal. Le seuil de réussite est de 70 %, et les deux
exigences bloquantes doivent être tenues. Le retour se limite à la liste des
critères non satisfaits et à la note.

```bash
dsoxlab check k8s-challenge-durcir-les-noeuds-et-l-acces-api
```
