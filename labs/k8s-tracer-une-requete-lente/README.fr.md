# Tracer une requête lente à travers le maillage Istio

Lab guidé de la leçon « Tracer une requête lente à travers le maillage Istio »,
niveau 6 « Réseau avancé » de la formation Kubernetes (CKNE). Envoyer les spans
d'un waypoint vers un collecteur OpenTelemetry et Jaeger, trouver pourquoi
aucune n'arrive, faire suivre le contexte de trace par l'application, et nommer
le service lent à partir d'une seule trace.

| | |
|---|---|
| Cible | `k8s-cp.lab`, le cluster kubeadm du catalogue, agrandi du second worker optionnel `k8s-w2.lab` ; le lab installe Istio 1.32 en mode ambient, un collecteur OpenTelemetry contrib 0.165.0 et Jaeger 2.23.0 |
| Durée | environ 40 minutes |
| Prérequis | le lab `k8s-servir-une-gateway-en-https` (même maillage, même cluster) |
| Page liée | [Formation Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/), en attendant la publication de la leçon |

Le `run` de ce lab monte `k8s-w2.lab` s'il ne tourne pas encore, et le joint au
cluster. Chaque `run` ramène Istio au profil du lab, ce qui efface un
fournisseur de traces laissé par une tentative précédente, et tire de nouveau
le service lent. Le `cleanup.yaml` supprime les namespaces `boutique` et
`observabilite`, désinstalle Istio avec ses CRD, puis draine le second worker
et le retire du cluster : la machine virtuelle reste debout pour le lab suivant
qui en a besoin.

```bash
dsoxlab run   k8s-tracer-une-requete-lente
dsoxlab check k8s-tracer-une-requete-lente
```
