# Composer un Pod multi-conteneurs : init container, sidecar natif, volumes partagés

Challenge de la formation Kubernetes, dans la section Mettre en pratique de la
leçon « Init containers et sidecars » : un Deployment dont chaque Pod prépare
sa page avec un init container, la sert en lecture seule, et relaie son
journal d'accès par un sidecar natif depuis un volume partagé et borné. Cinq
exigences, seuil 80 %, deux bloquantes.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm ; le lab pose le namespace `photo` |
| Durée | environ 40 minutes |
| Pages associées | [Init containers et sidecars](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/init-containers-sidecars/#mettre-en-pratique), [Volumes applicatifs](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/volumes-applicatifs/) |

```bash
dsoxlab run    k8s-challenge-composer-un-pod-multi-conteneurs
dsoxlab check  k8s-challenge-composer-un-pod-multi-conteneurs
dsoxlab submit k8s-challenge-composer-un-pod-multi-conteneurs
```
