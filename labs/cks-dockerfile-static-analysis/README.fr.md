# Corriger un Dockerfile que l'analyse statique refuse, sans changer l'application

Lab **CKS**, domaine *Supply Chain Security* (20 % de l'épreuve), compétence
« Minimize base image footprint ».

C'est le pendant amont de `cks-image-scanning-trivy`, avec le même outil : là
on mesure ce qu'une image **contient**, ici ce que sa recette **promet**.

Mesuré le 2026-09-16 avec Trivy 0.74.0 : le Dockerfile de départ porte **cinq
constats** (tag `latest`, exécution en root, port 22 exposé, aucun
`HEALTHCHECK`, `apt-get` sans `--no-install-recommends`), et la version
corrigée n'en porte **aucun**.

Le dernier test cherche les cinq constats par leur **numéro**, et non par un
total. Un test qui exigerait « zéro constat » deviendrait rouge tout seul le
jour où Trivy ajouterait une règle, sans que le Dockerfile ait changé d'une
ligne : le catalogue annoncerait une régression qui n'existe pas.

Un autre test refuse la suppression du Dockerfile : une analyse qui n'a rien à
analyser ne reproche rien, et c'est le contournement le plus simple d'un test
qui compterait.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 20 minutes |
| Leçon jumelée | [Supply Chain Security](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/supply-chain-security/) |

```bash
dsoxlab run   cks-dockerfile-static-analysis
dsoxlab check cks-dockerfile-static-analysis
```

Transposé de K8sExamLab le 2026-09-16, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
