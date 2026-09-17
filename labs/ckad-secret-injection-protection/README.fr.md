# Sortir un mot de passe d'un manifeste, sans que l'application s'en aperçoive

Lab **CKAD**, domaine *Application Environment, Configuration and Security*
(25 % de l'épreuve), les Secrets.

Distinct de [`ckad-configmap-secret-injection`](../ckad-configmap-secret-injection/),
qui porte sur l'injection depuis un ConfigMap. Celui-ci porte sur ce que le
Secret change vraiment : **la valeur quitte le manifeste**, et l'application ne
voit pas la différence.

Le test final exerce les deux côtés dans le **même** test, délibérément.
Séparées, ces deux moitiés ne mesureraient rien de bon :

| moitié isolée | pourquoi elle ne vaut rien seule |
|---|---|
| « la valeur n'est plus dans le manifeste » | vert si le candidat supprime la variable et casse l'application |
| « le conteneur voit la valeur » | déjà vrai AVANT le travail, le manifeste la lui donne en clair |

Le lab demande les **deux** chemins d'injection, parce qu'ils ne se valent pas :
une variable d'environnement est figée pour la vie du processus, un fichier
monté est rafraîchi quand le Secret change. C'est la raison pour laquelle une
application qui recharge sa configuration lit un fichier et non une variable.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 20 minutes |
| Leçon jumelée | [Secrets](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/secrets/) |

```bash
dsoxlab run   ckad-secret-injection-protection
dsoxlab check ckad-secret-injection-protection
```
