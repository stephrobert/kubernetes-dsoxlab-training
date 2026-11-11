# Une base Kustomize et deux overlays, dev et prod

Lab de la leçon **Kustomize** du module « Déployer ses applications » de la
formation Kubernetes, et compétence **CKAD** du domaine *Application
Deployment* : une base, deux overlays, une ConfigMap générée, un changement
d'image propre à un environnement, et un cluster conforme au dossier.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 30 minutes |
| Page associée | [Kustomize, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kustomize/#mettre-en-pratique) |

```bash
dsoxlab run   ckad-kustomize-overlays
dsoxlab check ckad-kustomize-overlays
```
