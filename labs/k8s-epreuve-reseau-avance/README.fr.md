# Épreuve du niveau 6 : exposer et protéger un service sur Cilium

Épreuve de fin du niveau 6 « Réseau avancé » de la formation Kubernetes
(CKNE). Exposer un service en HTTPS par un Gateway servi par Cilium, lui donner
un accès en lecture seule par une politique L7 qui ne coupe pas le Gateway,
chiffrer le trafic entre nœuds en WireGuard, et nommer d'après Hubble la
requête que la politique refuse. Notée sur l'état du cluster, réussie à 70 %,
avec deux contrôles bloquants et sans indice.

| | |
|---|---|
| Cible | `net-cp.lab`, le cluster Cilium sans kube-proxy des hôtes optionnels `net-cp`, `net-w1` et `net-w2` |
| Versions | Kubernetes 1.37, Cilium 1.20.5 (qui déclare Kubernetes 1.33 à 1.36), Gateway API v1.6.3, Helm 4.3.2 |
| Durée | environ 120 minutes |
| Prérequis | les labs du niveau 6, en particulier `k8s-installer-cilium-sans-kube-proxy` et `k8s-auditer-les-flux-avec-hubble` |
| Page liée | [Épreuve du niveau 6](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/epreuves/reseau-avance/) |

Le `run` de cette épreuve monte les hôtes `net-*` s'ils ne tournent pas
encore, ramène Cilium aux valeurs du socle, retire toute CRD de la Gateway API,
et pose l'état hérité. Le `cleanup.yaml` supprime l'espace `boutique` et les
pools d'adresses, ramène Cilium aux valeurs du socle, et seulement ensuite
retire les CRD de la Gateway API : dans l'autre ordre, Helm ne sait plus lire
la release Cilium.

```bash
dsoxlab run   k8s-epreuve-reseau-avance
dsoxlab check k8s-epreuve-reseau-avance
```
