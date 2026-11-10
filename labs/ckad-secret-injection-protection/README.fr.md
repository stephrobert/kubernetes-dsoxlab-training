# Sortir un mot de passe d'un manifeste, sans que l'application s'en aperçoive

Lab **CKAD**, domaine *Application Environment, Configuration and Security*
(25 % de l'épreuve), les Secrets.

Distinct de [`ckad-configmap-secret-injection`](../ckad-configmap-secret-injection/),
qui porte sur l'injection depuis un ConfigMap. Celui-ci porte sur ce que le
Secret change vraiment : **la valeur quitte le manifeste**, et l'application ne
voit pas la différence.

**Neuf tests, un par état demandé par l'énoncé**, chacun pesant le même
neuvième de la note. Deux d'entre eux portent tout le propos du lab :

| test | ce qu'il ferme |
|---|---|
| il lit le `.data` du Secret et le décode | le Secret n'est plus une formalité dont personne ne lit le contenu |
| il balaye les ConfigMaps du namespace à la recherche de la valeur | la valeur déplacée dans un ConfigMap quitte le manifeste et ne protège rien |

Sans ces deux-là, le mot de passe écrit en clair dans un ConfigMap et injecté
de là rendait la note pleine, soit l'inverse exact de ce que le lab enseigne.
Sortir une valeur d'un manifeste ne vaut rien en soi : ce qui compte est
l'objet où elle atterrit.

Aucune des deux moitiés « elle a quitté le manifeste » et « le conteneur la
voit » ne prouve quoi que ce soit seule, et cela reste vrai : la première est
verte si le candidat supprime la variable et casse l'application, la seconde est
déjà vraie AVANT le travail. Les deux sont donc exigées, en tests distincts,
pour qu'un travail incomplet s'entende dire quel état manque plutôt que le seul
premier échec.

Le lab demande les **deux** chemins d'injection, parce qu'ils ne se valent pas :
une variable d'environnement est figée pour la vie du processus, un fichier
monté est rafraîchi quand le Secret change. C'est la raison pour laquelle une
application qui recharge sa configuration lit un fichier et non une variable.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 20 minutes |
| Leçon jumelée | [Secrets](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/secrets/) |

```bash
dsoxlab run   ckad-secret-injection-protection
dsoxlab check ckad-secret-injection-protection
```
