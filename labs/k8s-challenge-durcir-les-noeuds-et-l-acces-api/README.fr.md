# Durcir un nœud worker et l'accès à l'API server, sans casser le cluster

Challenge du module **Identités, accès et nœuds** de la formation Kubernetes :
un nœud worker livré depuis un ancien modèle de serveur, à ramener à ce dont
Kubernetes a besoin (services, SSH, sudo, kubelet, pare-feu), puis un API
server à fermer à l'anonyme sans casser les sondes de santé ni `kubeadm join`.
Le nœud est redémarré à la fin pour vérifier que tout tient. Sept exigences,
seuil 70, deux bloquantes.

| | |
|---|---|
| Cible | `k8s-cp.lab` et le second worker optionnel `k8s-w2.lab`, joint au cluster kubeadm du catalogue le temps du challenge |
| Durée | environ 60 minutes |
| Page associée | [Durcir les nœuds](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/durcir-les-noeuds/) |

```bash
dsoxlab run    k8s-challenge-durcir-les-noeuds-et-l-acces-api
dsoxlab check  k8s-challenge-durcir-les-noeuds-et-l-acces-api
dsoxlab submit k8s-challenge-durcir-les-noeuds-et-l-acces-api
```
