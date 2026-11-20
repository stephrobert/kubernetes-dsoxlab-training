# Réparer, ouvrir, faire sortir et auditer les flux d'un cluster Cilium, sans guidage

Challenge du module **Réseau avancé** de la formation Kubernetes (niveau 6,
CKNE), dans la section Mettre en pratique de la leçon « Faire sortir le trafic
par une passerelle d'egress » : un Service servi par Cilium à réparer sans
kube-proxy, un seul flux à ouvrir entre deux namespaces, un namespace à faire
sortir par un nœud choisi, et le flux qu'une politique refuse à désigner en le
lisant dans Hubble. Quatre exigences, seuil 70.

| | |
|---|---|
| Cible | `net-cp.lab`, cluster Cilium 1.20.5 sans kube-proxy (`net-w1.lab`, `net-w2.lab`), passerelle d'egress et Hubble activés ; témoin externe sur `k8s-cp.lab` |
| Durée | environ 60 minutes |
| Page associée | [Faire sortir le trafic par une passerelle d'egress](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/reseau-avance/egress-gateway/) |

```bash
dsoxlab run    k8s-challenge-reseau-avance
dsoxlab check  k8s-challenge-reseau-avance
dsoxlab submit k8s-challenge-reseau-avance
```
