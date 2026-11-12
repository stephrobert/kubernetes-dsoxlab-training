# Installer un opérateur et configurer ce qu'il fait tourner

Lab **CKA**, domaine *Cluster Architecture, Installation and Configuration* :
« Understand CRDs, install and configure operators ». Lab guidé de la leçon
« Opérateurs » de la formation Kubernetes.

L'apprenant installe **MongoDB Controllers for Kubernetes 1.15.0** par ses deux
manifestes versionnés, images épinglées par digest, lui confie un replica set à
un membre, puis change un réglage de mongod en ne touchant qu'à la ressource.

L'opérateur a été choisi sur sa matrice de compatibilité officielle, qui couvre
Kubernetes 1.35, 1.36 et 1.37 (lue le 2026-11-12). Licences : Apache 2.0 pour
l'opérateur piloté sur MongoDB Community, SSPL v1 pour le serveur MongoDB.

Le setup installe `local-path-provisioner` v0.0.37 comme classe par défaut. Le
`cleanup.yaml` retire le namespace `mongodb`, les CRD, les droits de cluster et
la configuration de webhook de l'opérateur, puis le stockage et ses données sur
les deux nœuds.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 40 minutes, dont plusieurs pour tirer l'image du serveur (433 Mo) |
| Leçon jumelée | [Opérateurs](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operators/#mettre-en-pratique) |

```bash
dsoxlab run   cka-operateur-installer-et-configurer
dsoxlab check cka-operateur-installer-et-configurer
```
