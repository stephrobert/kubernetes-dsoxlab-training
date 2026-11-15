# Épreuve du niveau 4 : administrer un cluster

L'épreuve de fin du niveau 4 de la formation Kubernetes : administrer, à
partir d'un état hérité, le cluster kubeadm qui héberge la boutique. Ramener
un worker réinitialisé, prouver la haute disponibilité d'un plan de contrôle
derrière son répartiteur, sauvegarder etcd et restaurer la boutique depuis la
sauvegarde de la veille, migrer des manifestes hors des API retirées, monter
le cluster de 1.36.4 en 1.37.0, garder la boutique disponible pendant la
maintenance, réparer un nœud, un API server et un composant en consignant
d'abord chaque cause, reporter une modification faite en direct et
renouveler des certificats. Dix-huit critères, seuil 70, sept critiques, quatre
indices payants.

La haute disponibilité se joue sur un cluster kind à trois plans de contrôle,
sur `k8s-kind.lab`, parce que l'infrastructure du catalogue ne porte qu'un plan
de contrôle kubeadm. Le setup reconstruit le cluster kubeadm en 1.36.4, et le
nettoyage le reconstruit à la version du catalogue ; il supprime aussi les
clusters kind des autres labs, que chacun recrée par son propre setup.

| | |
|---|---|
| Cible | `k8s-cp.lab` et `k8s-w1.lab`, cluster kubeadm du catalogue ; `k8s-kind.lab`, où l'apprenant crée le cluster `ha` |
| Durée | environ 180 minutes |
| Page associée | [Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/) (provisoire, en attendant la page de l'épreuve) |

```bash
dsoxlab run    k8s-epreuve-administrer-un-cluster
dsoxlab check  k8s-epreuve-administrer-un-cluster
dsoxlab submit k8s-epreuve-administrer-un-cluster
```
