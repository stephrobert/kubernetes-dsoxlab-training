# Plafonner un namespace sans bloquer ceux qui oublient de se déclarer

Lab **CKA** et **CKAD**, domaine *Workloads and Scheduling* (15 % du CKA) et
*Application Environment* côté CKAD.

**Les deux objets vont ensemble, et c'est tout le sujet.** Poser le plafond
seul transforme l'oubli d'un développeur en refus incompréhensible : dès qu'un
quota porte sur les `requests`, un Pod qui n'en déclare pas devient invalide,
l'API ne pouvant décompter ce qui n'est pas déclaré. Le lab fait éprouver cette
dépendance plutôt que de l'énoncer.

**Les deux tests sont des preuves actives**, et opposées :

| sonde | attendu | pourquoi |
|---|---|---|
| un Pod demandant 64 CPU | **refusé à la création** | sans quota, l'API l'accepte et il reste Pending : personne ne l'a refusé |
| un Pod sans aucune ressource | **accepté, puis complété** | sans valeurs par défaut, il serait refusé par le quota lui-même |

Relire les objets posés ne prouverait rien : un ResourceQuota dont le `hard` ne
porte pas sur les bonnes ressources est parfaitement valide et ne plafonne
rien ; un LimitRange dont le `type` n'est pas le bon ne complète aucun
conteneur.

Le dernier contrôle vérifie que l'application du namespace tourne encore : un
plafond trop bas l'empêcherait de se replacer, et ce serait une panne.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 25 minutes |
| Leçon jumelée | [ResourceQuota et LimitRange](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/resource-quotas/) |

```bash
dsoxlab run   cka-resourcequota-limitrange
dsoxlab check cka-resourcequota-limitrange
```
