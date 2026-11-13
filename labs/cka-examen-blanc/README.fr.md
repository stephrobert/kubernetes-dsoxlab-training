# Examen blanc CKA : 17 tâches en 120 minutes

Capstone de certification de la formation Kubernetes, hébergé par la page
d'exercices CKA. Dix-sept tâches au format de l'examen, réparties comme les
domaines du programme officiel CKA v1.37, notées sur l'état final du cluster,
sans indice. Le seuil est celui de l'examen réel, 66 %, lu dans la FAQ CKA, CKAD
et CKS de la Linux Foundation.

Vingt états à 5 points : dsoxlab note la part de tests réussis, et une tâche de
10 % porte donc deux états.

| Domaine | Poids | Tâches |
|---|---|---|
| Storage | 10 | 1, 2 |
| Troubleshooting | 30 | 3, 4, 5, 6 |
| Workloads and Scheduling | 15 | 7, 8, 9 |
| Cluster Architecture, Installation and Configuration | 25 | 10, 11, 12, 13 |
| Servicing and Networking | 20 | 14, 15, 16, 17 |

Le setup installe Traefik (Ingress et Gateway API v1.6.2) et local-path, pose
un kubeconfig, l'alias `k` et la complétion sur les deux hôtes de tâche, puis met le kubelet du worker
hors service. Le `cleanup.yaml` remet le worker en service et retire tout, y
compris les objets du cluster entier.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm ; le worker `k8s-w1.lab` est en panne au départ |
| Durée | 120 minutes |
| Page associée | [Exercices CKA](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/certifications/cka/exercices/) |

```bash
dsoxlab run    cka-examen-blanc
dsoxlab check  cka-examen-blanc
dsoxlab submit cka-examen-blanc
```
