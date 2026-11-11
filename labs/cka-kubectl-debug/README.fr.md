# Entrer dans un conteneur sans shell avec kubectl debug

Lab de la leçon **Débugger une application** du module « Déployer ses
applications » de la formation Kubernetes, et compétence **CKA** du domaine
*Troubleshooting* : les images distroless n'ont ni shell ni outils, et
`kubectl exec` y échoue. Un conteneur éphémère qui partage les processus de
l'application permet d'y regarder quand même.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 10 minutes |
| Page associée | [Débugger une application, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/debug-applications/#mettre-en-pratique) |

```bash
dsoxlab run   cka-kubectl-debug
dsoxlab check cka-kubectl-debug
```
