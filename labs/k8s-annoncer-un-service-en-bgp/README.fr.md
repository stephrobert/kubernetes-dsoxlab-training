# Annoncer les Pods et les Services à un routeur en BGP

Lab guidé de la leçon « Annoncer des Services en BGP », niveau 6 « Réseau
avancé » de la formation Kubernetes (CKNE). Activer le plan de contrôle BGP de
Cilium, appairer les trois nœuds avec un routeur FRR externe, annoncer les
réseaux des Pods et une adresse de LoadBalancer, et joindre le Service depuis
le routeur.

| | |
|---|---|
| Cible | `net-cp.lab`, le cluster Cilium sans kube-proxy des hôtes optionnels `net-cp`, `net-w1` et `net-w2` ; le routeur FRR tourne sur `k8s-cp.lab`, hors de ce cluster |
| Versions | Kubernetes 1.37, Cilium 1.20.5 (qui déclare Kubernetes 1.33 à 1.36), FRR 10.6.2, Helm 4.3.2 |
| Durée | environ 40 minutes |
| Prérequis | le lab `k8s-installer-cilium-sans-kube-proxy` |
| Page liée | [Annoncer des Services en BGP](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/reseau-avance/annoncer-services-bgp/) |

Le `run` de ce lab monte les hôtes `net-*` s'ils ne tournent pas encore,
ramène Cilium aux valeurs du socle, et lance le routeur FRR sur
`k8s-cp.lab` : un conteneur lancé par `ctr`, dans un espace de noms réseau à
lui, derrière une interface macvlan à `10.10.50.200`, dans une unité systemd
transitoire. Le `cleanup.yaml` supprime les ressources BGP, le pool
d'adresses et le namespace `bgp-demo`, retire l'étiquette `bgp` des nœuds,
ramène Cilium aux valeurs du socle, et retire le routeur avec son espace de
noms.

```bash
dsoxlab run   k8s-annoncer-un-service-en-bgp
dsoxlab check k8s-annoncer-un-service-en-bgp
```
