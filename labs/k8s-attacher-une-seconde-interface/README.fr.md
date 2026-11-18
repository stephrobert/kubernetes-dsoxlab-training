# Donner une seconde interface réseau à un Pod avec Multus

Lab guidé de la leçon « Donner plusieurs interfaces à un Pod avec Multus »,
niveau 6 « Réseau avancé » de la formation Kubernetes (CKNE). Laisser Cilium
partager la configuration CNI, installer Multus 4.3.2 en mode thick, décrire un
réseau macvlan, et prouver un échange entre deux Pods par ce second réseau.

| | |
|---|---|
| Cible | `net-cp.lab`, le cluster Cilium sans kube-proxy des hôtes optionnels `net-cp`, `net-w1` et `net-w2` |
| Versions | Kubernetes 1.37, Cilium 1.20.5 (qui déclare Kubernetes 1.33 à 1.36), Multus v4.3.2 thick, Helm 4.3.2 |
| Durée | environ 35 minutes |
| Prérequis | le lab `k8s-installer-cilium-sans-kube-proxy` |
| Page liée | [Donner plusieurs interfaces à un Pod avec Multus](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/reseau-avance/pods-multi-interfaces/) |

Le `run` de ce lab monte les hôtes `net-*` s'ils ne tournent pas encore et
ramène Cilium aux valeurs du socle. Le `cleanup.yaml` supprime le namespace
`multus-demo`, retire Multus par son manifeste ainsi que les fichiers qu'il
laisse sur chaque nœud (d'abord `00-multus.conf`, qui enverrait sinon tout
nouveau Pod vers un Multus absent), puis ramène Cilium en
`cni.exclusive=true`.

```bash
dsoxlab run   k8s-attacher-une-seconde-interface
dsoxlab check k8s-attacher-une-seconde-interface
```
