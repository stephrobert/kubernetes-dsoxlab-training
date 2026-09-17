# Faire refuser une image non épinglée par le cluster lui-même, sans webhook

Lab **CKS**, domaine *Supply Chain Security* (20 % de l'épreuve), contrôle
d'admission.

Le voisin [`cks-image-pinned-digest`](../cks-image-pinned-digest/) fait
**épingler** une image. Celui-ci fait **refuser** celles qui ne le sont pas :
c'est le geste de l'exploitant, qui cesse de reposer sur la discipline de
chacun.

**ValidatingAdmissionPolicy est natif** depuis la 1.30 et stable depuis la
1.32 : aucun composant à installer, contrairement aux solutions par webhook,
dont la panne bloque toute création de Pod tant que leur `failurePolicy` vaut
`Fail`. C'est ce qui rend ce lab jouable en vingt lignes de YAML.

**Le test est une preuve active dans les deux sens.** Relire la politique ne
prouverait rien, et trois façons distinctes de se tromper produisent un objet
parfaitement valide :

| erreur | effet |
|---|---|
| politique sans liaison | n'agit sur aucune requête |
| `validationActions: [Warn]` | signale, et laisse passer |
| `exists` au lieu de `all` en CEL | laisse passer un Pod dont un conteneur sur deux est épinglé |

Mesuré le 2026-09-17 sur Kubernetes v1.37.0 : le refus porte le message de la
politique elle-même, `ValidatingAdmissionPolicy '<nom>' with binding '<nom>'
denied request: …`, et une image épinglée par digest passe dans la foulée.

Le `cleanup.yaml` supprime la liaison **puis** la politique, toutes deux objets
de **cluster** : laissées en place, elles refuseraient des Pods dans les labs
suivants. La ValidatingAdmissionPolicy `safe-upgrades` de la Gateway API, si
elle est présente, est épargnée.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 30 minutes |
| Leçon jumelée | [ValidatingAdmissionPolicy](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/validating-admission-policy/) |

```bash
dsoxlab run   cks-validating-admission-policy
dsoxlab check cks-validating-admission-policy
```
