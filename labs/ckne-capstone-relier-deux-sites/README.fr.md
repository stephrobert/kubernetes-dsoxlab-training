# Capstone : relier deux sites, annoncer un Service au réseau et le servir en HTTPS

Capstone de la certification **CKNE** de la formation Kubernetes (niveau 6),
dans la page des exercices chronométrés CKNE. Il ne nomme aucun objet : relier
deux sites pour que la boutique y réponde et survive à la perte de l'un,
l'annoncer en BGP au routeur de l'équipe réseau, et la servir en HTTPS sous son
nom public avec un certificat de cert-manager, le HTTP étant redirigé. Trois
exigences, toutes bloquantes, seuil 70.

| | |
|---|---|
| Cible | `ha-cp1.lab` (site 1) et `ha-cp2.lab` (site 2), deux clusters Cilium 1.20.5 d'un nœud sans kube-proxy ; routeur FRR 10.6.2 de l'équipe réseau sur `k8s-cp.lab` |
| Durée | environ 75 minutes |
| Page associée | [Exercices chronométrés CKNE](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/certifications/ckne/exercices/) |

```bash
dsoxlab run    ckne-capstone-relier-deux-sites
dsoxlab check  ckne-capstone-relier-deux-sites
dsoxlab submit ckne-capstone-relier-deux-sites
```
