# Monter un plan de contrôle kubeadm à trois nœuds derrière un répartiteur, et en perdre un

Lab **CKA**, domaine *Cluster Architecture, Installation and Configuration*,
compétence « Implement and configure a highly-available control plane ».

Un plan de contrôle unique est un point de défaillance unique. Ce lab fait
monter, avec kubeadm, trois plans de contrôle à etcd empilé derrière un
répartiteur HAProxy, puis prouve la haute disponibilité en arrêtant l'un
d'eux.

| | |
|---|---|
| Cibles | `ha-cp1.lab`, `ha-cp2.lab`, `ha-cp3.lab` et le répartiteur `ha-lb.lab`, hôtes optionnels montés pour ce lab seulement |
| Durée | environ 40 minutes |
| Leçon jumelée | [Haute disponibilité du control plane](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/ha-control-plane/) |

Ce lab ajoute quatre machines au catalogue le temps de le jouer. Elles
restent après `dsoxlab clean` ; `dsoxlab destroy --optional-hosts` les retire.

```bash
dsoxlab run   cka-control-plane-haute-disponibilite
dsoxlab check cka-control-plane-haute-disponibilite
```
