# Examen blanc CKAD : 17 tâches en 120 minutes

Capstone de certification de la formation Kubernetes, hébergé par la page
d'exercices CKAD. Dix-sept tâches au format de l'examen, réparties comme les
domaines du programme officiel CKAD v1.37, notées sur l'état final du cluster,
sans indice. Le seuil est celui de l'examen réel, 66 %, lu dans la FAQ CKA, CKAD
et CKS de la Linux Foundation.

Vingt états à 5 points : dsoxlab note la part de tests réussis, et une tâche de
10 % porte donc deux états.

| Domaine | Poids | Tâches |
|---|---|---|
| Application Design and Build | 20 | 1, 2, 3 |
| Application Deployment | 20 | 4, 5, 6 |
| Application Observability and Maintenance | 15 | 7, 8, 9 |
| Application Environment, Configuration and Security | 25 | 10, 11, 12, 13, 14 |
| Services and Networking | 20 | 15, 16, 17 |

Helm et la construction d'images sont hors parcours dans le référentiel : ils ne
figurent pas dans l'examen. Le setup installe Traefik et local-path, et pose
trois contextes dans le kubeconfig de l'apprenant.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm |
| Durée | 120 minutes |
| Page associée | [Exercices CKAD](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/certifications/ckad/exercices/) |

```bash
dsoxlab run    ckad-examen-blanc
dsoxlab check  ckad-examen-blanc
dsoxlab submit ckad-examen-blanc
```
