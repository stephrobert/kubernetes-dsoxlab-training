# Installer un cluster kubeadm, y joindre un nœud et rendre le plan de contrôle hautement disponible

Challenge du module **Installer un cluster** de la formation Kubernetes (niveau
4), dans la section Mettre en pratique de la leçon « Haute disponibilité » :
un worker réinitialisé à préparer et à joindre au cluster kubeadm pour qu'il
survive à un redémarrage, un Pod forcé sur lui, puis un cluster kind à trois
plans de contrôle derrière son répartiteur, qui doit tenir la perte de l'un
d'eux. Sept états, seuil 70, deux bloquants.

Les états de haute disponibilité se jouent sur kind parce que l'infrastructure
du catalogue ne porte qu'un plan de contrôle kubeadm : kind pose lui-même le
répartiteur, et ses nœuds sont des machines kubeadm à etcd empilé. Le setup
supprime les clusters kind des autres labs pour libérer la mémoire ; chacun
les recrée par son propre setup.

| | |
|---|---|
| Cible | `k8s-cp.lab` et `k8s-w1.lab`, cluster kubeadm du catalogue ; `k8s-kind.lab`, où l'apprenant crée le cluster `ha` |
| Durée | environ 60 minutes |
| Page associée | [Haute disponibilité](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/ha-control-plane/) |

```bash
dsoxlab run    k8s-challenge-installer-un-cluster
dsoxlab check  k8s-challenge-installer-un-cluster
dsoxlab submit k8s-challenge-installer-un-cluster
```
