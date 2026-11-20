# Retrouver, compter et journaliser les flux refusés avec Hubble

Challenge de la formation Kubernetes, dans la section Mettre en pratique de la
leçon « Hubble » : retrouver le flux qu'une politique de sortie refuse et le
nœud qui le voit, faire nommer sa source et sa destination à la métrique des
refus, et journaliser les seuls refus d'un namespace. Trois exigences, seuil
70 %, deux bloquantes.

| | |
|---|---|
| Cible | `net-cp.lab`, plan de contrôle du cluster Cilium sans kube-proxy, avec `net-w1.lab` et `net-w2.lab` |
| Durée | environ 45 minutes |
| Page associée | [Hubble, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/hubble/#mettre-en-pratique) |

```bash
dsoxlab run    k8s-challenge-retrouver-les-flux-refuses
dsoxlab check  k8s-challenge-retrouver-les-flux-refuses
dsoxlab submit k8s-challenge-retrouver-les-flux-refuses
```
