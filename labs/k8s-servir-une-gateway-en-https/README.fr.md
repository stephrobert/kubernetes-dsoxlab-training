# Servir une Gateway d'Istio en HTTPS avec un certificat de cert-manager

Lab guidé de la leçon « Servir une Gateway en HTTPS avec cert-manager », niveau
6 « Réseau avancé » de la formation Kubernetes (objectif CKNE « Managing TLS
Certificates for Gateway API »). Demander un certificat à cert-manager dans le
namespace de la Gateway, déclarer une Gateway d'Istio avec un listener HTTPS
qui le présente, y attacher une route, et prouver le résultat par un vrai
client TLS.

| | |
|---|---|
| Cible | `k8s-cp.lab`, le cluster kubeadm du catalogue, agrandi du second worker optionnel `k8s-w2.lab` ; le lab installe Istio 1.32 en mode ambient, la Gateway API v1.6.1 et cert-manager v1.21.3 |
| Durée | 35 minutes environ |
| Prérequis | le lab cert-manager `k8s-emettre-un-certificat-avec-cert-manager` (niveau 4) |
| Page associée | [Formation Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/), en attendant la publication de la leçon |

Le `run` de ce lab monte `k8s-w2.lab` s'il ne tourne pas encore, et le joint au
cluster. Le `cleanup.yaml` supprime le namespace `vitrine`, retire cert-manager
par son manifeste officiel, désinstalle Istio et ses CRD, puis draine le second
worker et le retire du cluster : la machine virtuelle reste debout pour le
prochain lab qui en a besoin.

```bash
dsoxlab run   k8s-servir-une-gateway-en-https
dsoxlab check k8s-servir-une-gateway-en-https
```
