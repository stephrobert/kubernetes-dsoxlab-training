# Faire sortir le trafic d'un Pod par une passerelle d'egress

Lab guidé de la leçon « Faire sortir le trafic par une passerelle d'egress »,
niveau 6 « Réseau avancé » de la formation Kubernetes (CKNE). Activer la
passerelle d'egress de Cilium avec le masquage BPF qu'elle exige, désigner un
nœud passerelle, et faire joindre un serveur externe par ce nœud à un Pod, et à
lui seul.

| | |
|---|---|
| Cible | `net-cp.lab`, le cluster Cilium sans kube-proxy des hôtes optionnels `net-cp`, `net-w1` et `net-w2` ; le serveur témoin tourne sur `k8s-cp.lab`, hors de ce cluster |
| Versions | Kubernetes 1.37, Cilium 1.20.5 (qui déclare Kubernetes 1.33 à 1.36), Helm 4.3.2 |
| Durée | environ 30 minutes |
| Prérequis | le lab `k8s-installer-cilium-sans-kube-proxy` |
| Page liée | [Passerelle d'egress](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/reseau-avance/egress-gateway/) |

Le `run` de ce lab monte les hôtes `net-*` s'ils ne tournent pas encore,
ramène Cilium aux valeurs du socle, et lance le serveur témoin sur
`k8s-cp.lab` (port 8090, unité systemd transitoire). Le `cleanup.yaml`
supprime les politiques et le namespace `egress-demo`, retire l'étiquette de
passerelle des nœuds, ramène Cilium aux valeurs du socle, et arrête le témoin.

```bash
dsoxlab run   k8s-faire-sortir-le-trafic-par-une-passerelle
dsoxlab check k8s-faire-sortir-le-trafic-par-une-passerelle
```
