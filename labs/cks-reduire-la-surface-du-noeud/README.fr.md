# Retirer d'un worker ce qui écoute sans servir Kubernetes

Lab **CKS**, domaine *System Hardening* (10 % de l'épreuve), compétence
« Minimize host OS footprint (reduce attack surface) ».

Un nœud Kubernetes n'a besoin que d'une poignée de ports et de services. Tout
le reste agrandit la surface d'attaque sans rien apporter. Ce lab vous fait
relier chaque port ouvert à sa source, puis retirer durablement ce qui ne sert
pas, sans sortir le nœud du cluster.

| | |
|---|---|
| Cible | `k8s-w2.lab`, second worker du cluster kubeadm (hôte optionnel), joint depuis `k8s-cp.lab` |
| Durée | environ 20 minutes |
| Leçon jumelée | [Durcir les nœuds](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/durcir-les-noeuds/) |

```bash
dsoxlab run   cks-reduire-la-surface-du-noeud
dsoxlab check cks-reduire-la-surface-du-noeud
```

Le lab monte `k8s-w2.lab` s'il ne tourne pas. Si vous retirez par erreur un
paquet indispensable, `dsoxlab destroy --optional-hosts` retire la machine, et
le prochain `dsoxlab run` la remonte.
