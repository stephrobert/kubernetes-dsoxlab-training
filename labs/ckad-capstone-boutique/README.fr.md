# Capstone : livrer la boutique, à partir du seul cahier des charges

Premier **capstone CKAD** du catalogue. Il ne vise pas une compétence du
blueprint, il en croise cinq : *Application Design and Build*, *Application
Deployment*, *Application Environment, Configuration and Security*,
*Application Observability* et *Services and Networking*.

Un micro-lab annonce son sujet dans son titre. `cka-troubleshoot-dns` apprend
à réparer le DNS, et prévient que le problème est le DNS : l'apprenant peut
devenir très bon à cet exercice sans jamais avoir eu à trouver où regarder.
Ce capstone ne nomme aucun objet Kubernetes. Il donne six exigences et un
namespace vide, et laisse le candidat choisir ses outils, comme l'épreuve.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 45 minutes |
| Seuil de réussite | 66 %, celui de l'examen CKAD |
| Leçon jumelée | [Exercices CKAD](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/certifications/ckad/exercices/) |

```bash
dsoxlab run    ckad-capstone-boutique
dsoxlab check  ckad-capstone-boutique
dsoxlab submit ckad-capstone-boutique
```

Dix tests, dont la moitié entrent dans le conteneur : un manifeste conforme
qui ne produit pas l'effet attendu ne rapporte rien. Le dernier prouve
l'isolation dans les deux sens, `frontend` qui passe et `intrus` qui est
bloqué.

Écrit le 2026-09-15, puis validé par `scripts/valider-labs.py` : 0 avant le
travail, 100 après la solution du formateur, rejouable et sans trace.
