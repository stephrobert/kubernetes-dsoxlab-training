# Installer, mettre à jour et revenir en arrière avec Helm 4

Lab **CKAD**, domaine *Application Deployment* (20 % de l'épreuve),
compétence « Use the Helm package manager to deploy existing packages ».

Helm 4.3.0, la version courante. Le lab hérité passait par les charts
Bitnami, dont les images ne sont plus librement servies : le chart est local,
généré par `helm create`, image alignée sur le reste du catalogue.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Installer et gérer des releases Helm](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/helm/install-releases/) |

```bash
dsoxlab run   ckad-helm-install-upgrade
dsoxlab check ckad-helm-install-upgrade
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
