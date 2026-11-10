# Régler une mise à jour progressive : maxSurge et maxUnavailable

Lab **CKAD**, domaine *Application Deployment* (20 % de l'épreuve),
compétence « Understand Deployments and how to perform rolling updates ».

Le lab hérité demandait un ConfigMap « evidence » recopiant les valeurs :
il ne prouvait rien. Ici chaque état demandé se lit sur le cluster. La
stratégie se lit là où elle vit, sur le Deployment : c'est elle, et elle
seule, qui dit sous quelles contraintes se jouera le prochain remplacement.
Les ReplicaSets, l'ancien à zéro et le nouveau au complet, disent autre
chose, et de plus étroit : qu'un remplacement a eu lieu, par ce Deployment,
et qu'il est allé au bout. Ils ne disent pas qu'il s'est joué sous les
contraintes demandées, et rien ne peut le dire après coup.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Rolling Updates et Rollbacks](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rolling-updates-rollbacks/) |

```bash
dsoxlab run   ckad-rolling-update-strategy
dsoxlab check ckad-rolling-update-strategy
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.

Réécrit le 2026-11-10 après une contre-expertise indépendante : les trois
tests précédents rendaient 100 sur un Deployment recréé de zéro et décoré
d'un ReplicaSet orphelin. Neuf critères alors, un par état demandé, chaque
ReplicaSet contrôlé sur son propriétaire et son numéro de révision.

Corrigé le même jour, après une campagne qui a mesuré **3 tests sur 9 verts
avant le travail** : un test qui passe sur la situation de départ donne des
points pour l'état initial. Huit critères désormais.

- La stratégie : `RollingUpdate` étant le défaut de Kubernetes, l'exigence ne
  pouvait rien refuser. C'est la situation qui a changé, `fixtures/prepare.sh`
  posant désormais `type: Recreate`. Le sujet y gagne : l'apprenant voit la
  différence entre les deux stratégies.
- Les cinq replicas prêts : ils l'étaient au départ, sur l'ancienne image. Le
  test exige maintenant l'état final complet, l'image de la révision active
  comprise.
- Les cinq replicas voulus : exigence de non-régression, vraie avant le
  travail par construction. Elle n'a plus de critère à elle et vit comme
  assertion du test précédent.

**Cette réécriture n'a pas encore été rejouée contre un cluster** :
l'attestation 0 puis 100 ci-dessus porte sur les tests précédents, pas sur
ceux-ci.
