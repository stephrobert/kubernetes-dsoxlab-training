# Changer de contexte et fixer le namespace par défaut

Lab guidé du module **Fondamentaux** de la formation Kubernetes, leçon
« Kubeconfig et contextes » : basculer de contexte, régler le namespace par
défaut, et constater où une commande sans `-n` ni `--context` envoie ce qu'elle
crée.

La préparation réunit déjà les deux clusters dans `~/.kube/config` : la fusion de
deux kubeconfigs est un approfondissement facultatif de la leçon, et ce lab ne
la note pas. La ConfigMap `preuve` sert de contrôle : elle doit se trouver dans
`kube-system` du cluster de recette, et nulle part dans `boutique`.

| | |
|---|---|
| Cible | `k8s-kind.lab`, clusters kind `boutique` (contexte de départ) et `lab` (le contexte `recette`) |
| Durée | environ 15 minutes |
| Page associée | [Kubeconfig et contextes, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-contexte/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-changer-de-contexte
dsoxlab check k8s-changer-de-contexte
```
