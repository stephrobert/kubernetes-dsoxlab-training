# Lire l'état d'un Pod en erreur

Lab **CKAD**, domaine *Application Observability and Maintenance*,
compétences « Use built-in CLI tools to monitor Kubernetes applications » et
« Utilize container logs ».

Le premier réflexe face à un Pod qui ne démarre pas : lire son état avant de
toucher à quoi que ce soit, avec `get`, `describe`, `logs` et `top`.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `lab` (Kubernetes 1.37) |
| Durée | environ 20 minutes |
| Leçon jumelée | [Lire l'état du cluster](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-get-describe-logs-top/) |

```bash
dsoxlab run   k8s-lire-l-etat-d-un-pod-en-erreur
dsoxlab check k8s-lire-l-etat-d-un-pod-en-erreur
```

Lab du module Fondamentaux de la formation, qui enseigne sur kind : il tourne
sur un cluster kind, et non sur le cluster kubeadm du catalogue.
