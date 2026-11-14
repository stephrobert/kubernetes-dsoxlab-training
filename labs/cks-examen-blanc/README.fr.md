# Examen blanc CKS : 16 tâches en 120 minutes

Capstone de certification de la formation Kubernetes, hébergé par la page
d'exercices CKS. Seize tâches au format de l'examen, réparties comme les six
domaines du programme officiel CKS v1.37, notées sur l'état final du cluster,
sans indice. Le seuil est celui de l'examen réel, 67 %.

Vingt états à 5 points : dsoxlab note la part de tests réussis, et une tâche à
10 % porte donc deux états.

| Domaine | Poids | Tâches |
|---|---|---|
| Cluster Setup | 15 | 1, 2, 3 |
| Cluster Hardening | 15 | 4, 5 |
| System Hardening | 10 | 6, 7 |
| Minimize Microservice Vulnerabilities | 20 | 8, 9, 10 |
| Supply Chain Security | 20 | 11, 12, 13 |
| Monitoring, Logging and Runtime Security | 20 | 14, 15, 16 |

La préparation installe Traefik, trivy 0.74.0, cosign 3.1.3 et crane 0.22.1, un
registre local, et l'état de départ de chaque tâche : un profileur resté
ouvert, un compte de service lié à cluster-admin, un Pod privilégié, une clé
d'API en clair, une image par tag, une image non signée, un API server qui
n'audite rien, un mineur caché dans un Pod sur quatre. Le profil AppArmor n'est
déposé que sur le worker. Le `cleanup.yaml` rend les manifestes du plan de
contrôle et retire tout, objets du cluster entier et fichiers des nœuds compris.

Istio, Falco et gVisor ne sont pas installés : le nœud de contrôle a 4 Go, et un
examen blanc doit tenir dans le délai du validateur. Le chiffrement entre Pods
et les runtimes en bac à sable restent dans leurs labs unitaires
(`cks-istio-mtls-lockdown`, `cks-runtime-sandbox-gvisor`) ; le mineur de la
tâche 16 se trouve sans Falco.

| | |
|---|---|
| Cible | `k8s-cp.lab`, plan de contrôle du cluster kubeadm ; les tâches 6 et 16 se jouent sur le worker `k8s-w1.lab` |
| Durée | 120 minutes |
| Page associée | [Exercices CKS](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/certifications/cks/exercices/) |

```bash
dsoxlab run    cks-examen-blanc
dsoxlab check  cks-examen-blanc
dsoxlab submit cks-examen-blanc
```
