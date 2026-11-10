# Basculer le trafic d'une version à l'autre : blue-green

Lab **CKAD**, domaine *Application Deployment* (20 % de l'épreuve),
compétence « Use Kubernetes primitives to implement common deployment
strategies (blue/green or canary) ».

Le lab hérité vérifiait le selector du Service sans jamais faire de requête.
La première réécriture faisait six requêtes à travers le Service, mais
n'interrogeait jamais la version blue : `app-blue` pouvait être un
`sleep 3600` sans aucun serveur et le lab rendait quand même 100. Depuis la
réécriture du 2026-11-10, chaque Pod de chaque version est interrogé **sur sa
propre adresse**, donc blue doit rester debout et servante, ce qui est la
seule raison pour laquelle un retour arrière blue-green est instantané.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Rolling Updates et Rollbacks](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rolling-updates-rollbacks/) |

Dix critères, un par état demandé par l'énoncé : les deux Deployments
(replicas, labels, version servie), le Service (port, selector, endpoints), et
les six requêtes depuis le client.

```bash
dsoxlab run   ckad-blue-green-deployment
dsoxlab check ckad-blue-green-deployment
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace. **La réécriture du 2026-11-10 n'a pas
encore été rejouée sur un cluster** : une campagne tournait sur le catalogue,
le cycle doit donc être rejoué avant de déclarer ce lab attesté.
