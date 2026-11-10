# Exposer un Deployment par un Service ClusterIP

Lab **CKAD**, domaine *Services and Networking* (20 % de l'épreuve),
compétence « Provide and troubleshoot access to applications via services ».

Le lab hérité lisait six specs sans jamais faire de requête. Ici onze critères
mesurent chacun un état demandé : le Deployment et l'image des Pods qu'il fait
réellement tourner, le Service avec ses ports, son selector et ses endpoints
prêts, puis dix requêtes depuis un client. Les réponses sont comparées à la
liste RÉELLE des Pods, et chaque Pod est interrogé sur sa propre boucle locale :
un conteneur qui sert un identifiant inventé est refusé.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 10 minutes |
| Leçon jumelée | [Les Services](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/) |

```bash
dsoxlab run   ckad-expose-service
dsoxlab check ckad-expose-service
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
