# Servir un Gateway et filtrer en L7 avec Cilium

Lab guidé de la leçon « Servir un Gateway et filtrer en L7 avec Cilium »,
niveau 6 « Réseau avancé » de la formation Kubernetes (CKNE). Activer la
Gateway API de Cilium, servir une application par un Gateway, et lui donner un
accès en lecture seule par une politique L7 qui ne coupe pas le Gateway.

| | |
|---|---|
| Cible | `net-cp.lab`, le cluster Cilium sans kube-proxy des hôtes optionnels `net-cp`, `net-w1` et `net-w2` |
| Versions | Kubernetes 1.37, Cilium 1.20.5 (qui déclare Kubernetes 1.33 à 1.36), Gateway API v1.6.3, Helm 4.3.2 |
| Durée | environ 35 minutes |
| Prérequis | le lab `k8s-installer-cilium-sans-kube-proxy` |
| Page liée | [Servir un Gateway et filtrer en L7 avec Cilium](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/reseau-avance/cilium-gateway-l7/) |

Le `run` de ce lab monte les hôtes `net-*` s'ils ne tournent pas encore,
ramène Cilium aux valeurs du socle et retire toute CRD de la Gateway API. Le
`cleanup.yaml` supprime le namespace `catalogue` et les pools d'adresses,
ramène Cilium aux valeurs du socle, et seulement ensuite retire les CRD de la
Gateway API : dans l'autre ordre, Helm ne sait plus lire la release Cilium.

```bash
dsoxlab run   k8s-filtrer-en-l7-avec-cilium
dsoxlab check k8s-filtrer-en-l7-avec-cilium
```
