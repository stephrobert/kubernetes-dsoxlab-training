# Router des requêtes d'inférence selon la charge des réplicas avec la Gateway API Inference Extension

Lab guidé de la leçon « Router du trafic d'inférence », niveau 6 « Réseau
avancé » de la formation Kubernetes (objectif CKNE « Optimizing LLM
Traffic »). Regrouper trois réplicas d'un serveur de modèle simulé dans un
`InferencePool`, le servir par une Gateway d'Istio, et prouver que les requêtes
suivent la charge des réplicas.

| | |
|---|---|
| Cible | `k8s-cp.lab`, le cluster kubeadm du catalogue, agrandi du second worker optionnel `k8s-w2.lab` ; le lab installe Istio 1.32 en mode ambient avec l'Inference Extension (CRD v1.5.0), le sélecteur d'endpoints v1.5.0 et le simulateur de vLLM `llm-d-inference-sim` v0.7.1 |
| Durée | 35 minutes environ |
| Page associée | [Formation Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/), en attendant la publication de la leçon |

La charge du réplica saturé est **simulée** : le simulateur publie des
métriques fixes (`--fake-metrics`), seul moyen fiable de garder une charge
stable sans GPU. Le sélecteur d'endpoints les lit exactement comme celles d'un
vrai vLLM.

Le `run` de ce lab monte `k8s-w2.lab` s'il ne tourne pas encore, et le joint au
cluster. Le `cleanup.yaml` supprime le namespace `inference`, désinstalle Istio
avec les CRD de la Gateway API et de l'Inference Extension, puis draine le
second worker et le retire du cluster.

```bash
dsoxlab run   k8s-router-des-requetes-d-inference
dsoxlab check k8s-router-des-requetes-d-inference
```
