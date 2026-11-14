# Ne laisser entrer que des images vérifiées, sans guidage

Challenge du module **Chaîne d'approvisionnement** de la formation Kubernetes,
dans la section Mettre en pratique de la leçon « Image Scanning (Grype/Trivy) » :
un Deployment à épingler sur son digest, un Dockerfile à débarrasser des
constats de l'analyse statique, une image à signer avec sa clé publique
publiée, une image vulnérable à remplacer, et un cluster qui doit refuser les
images non signées dès la création. Dix états, seuil 70, trois bloquants.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm du catalogue ; le lab pose le namespace `livraison`, un registre local sur le port 5000 du nœud, et Kyverno 1.19.2 sans politique |
| Durée | environ 60 minutes |
| Page associée | [Image Scanning (Grype/Trivy)](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/image-scanning/) |

```bash
dsoxlab run    k8s-challenge-livrer-une-image-verifiee
dsoxlab check  k8s-challenge-livrer-une-image-verifiee
dsoxlab submit k8s-challenge-livrer-une-image-verifiee
```
