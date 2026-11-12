# Réparer le réseau des Pods d'un nœud et lire ce que dit le réseau

Lab **CKA**, domaine *Troubleshooting* (30 % de l'épreuve). Lab guidé de la leçon
« Pod Networking » de la formation Kubernetes, dont il reprend les gestes : lire
les plages d'adresses, joindre un Pod d'un autre nœud, réparer un nœud dont le
réseau des Pods est tombé, distinguer un refus immédiat d'un délai dépassé.

La panne est mesurée sur le cluster du catalogue (Calico), le 2026-11-12 : sans
son fichier CNI, le worker passe NotReady en moins de 10 s, un Pod qu'on y place
reste en `ContainerCreating` (`cni plugin not initialized`), et Calico ne réécrit
pas le fichier de lui-même. Supprimer le Pod `calico-node` du worker le fait
réécrire : le nœud revient en 5 s.

Le setup tire au sort lequel des deux Services refuse et lequel fait attendre.
Le `cleanup.yaml` remet le fichier CNI s'il manque, fait réécrire la
configuration par Calico, attend le worker Ready, puis retire le namespace.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm ; la panne est sur `k8s-w1.lab` |
| Durée | environ 30 minutes |
| Leçon jumelée | [Pod Networking](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/pod-networking/#mettre-en-pratique) |

```bash
dsoxlab run   cka-troubleshoot-networking
dsoxlab check cka-troubleshoot-networking
```
