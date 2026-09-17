# Monter un cluster d'une version mineure, sans interrompre ce qui tourne

Lab **CKA**, domaine *Cluster Architecture, Installation and Configuration*
(25 % de l'épreuve), compétence « Perform a version upgrade on a Kubernetes
cluster using kubeadm ».

**C'était le dernier trou du CKA, et le plus net** : la formation enseigne
cette tâche, et aucun lab ne la faisait jouer.

## Pourquoi il a fallu attendre

L'issue #32 le classait bloqué, et la mesure du 2026-09-17 a montré comment le
débloquer :

| dépôt | versions publiées |
|---|---|
| `v1.37` | 1.37.0-1.1 |
| `v1.36` | 1.36.0-1.1, 1.36.1-1.1, 1.36.2-2.1, 1.36.3-1.1, 1.36.4-1.1 |

Il n'y a donc **rien à monter à l'intérieur de la 1.37**. Le cluster doit
partir en 1.36 pour qu'une montée existe, et c'est la montée **mineure** que
l'examen demande.

## Ce lab est le seul du catalogue à reconstruire le cluster

Son `setup.yaml` inclut d'abord le socle standard, qui garantit un cluster
sain, puis le ramène en **1.36.4** par un `kubeadm reset` et un `init`. Son
`cleanup.yaml` le **remonte** en 1.37.0. Il monte, il ne reconstruit pas : un
second `reset` serait bien plus risqué qu'une montée.

Sans ce cleanup, deux dégâts : la photographie du validateur verrait une
version différente de celle de départ, et surtout le lab **suivant** hériterait
d'un cluster dégradé.

Les deux fichiers portent une garde de version et sont donc idempotents : sur
un cluster déjà à la bonne version, ils ne touchent à rien.

## Ce que le test attrape

Le dernier test réunit trois contrôles, délibérément :

| contrôle | ce qu'il attrape |
|---|---|
| la version de **chaque** nœud | `kubeadm upgrade apply` ne monte pas le kubelet : un nœud oublié annonce l'ancienne version sans que rien ne casse |
| aucun nœud inordonnançable | un nœud vidé pour la montée et jamais rendu : le cluster tourne avec un nœud en moins, et rien ne le signale |
| les deux exemplaires prêts | déjà vrai AVANT le travail, donc sans valeur seul ; accolé aux deux autres, il distingue une montée conduite d'une montée qui a emporté le service |

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 40 minutes |
| Leçon jumelée | [Mettre à jour un cluster Kubernetes](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/mettre-a-jour-cluster-kubernetes/) |

```bash
dsoxlab run   cka-kubeadm-upgrade
dsoxlab check cka-kubeadm-upgrade
```
