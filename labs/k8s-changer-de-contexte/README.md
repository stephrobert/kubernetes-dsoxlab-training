# Switch context and set the default namespace

Guided lab of the **Fundamentals** module of the Kubernetes course, lesson
"Kubeconfig and contexts": switch context, set the default namespace, and see
where a command with neither `-n` nor `--context` sends what it creates.

The preparation already gathers both clusters in `~/.kube/config`: merging two
kubeconfigs is an optional deep dive of the lesson, and this lab does not grade
it. The ConfigMap `preuve` is the control: it must be in `kube-system` of the
recette cluster, and nowhere in `boutique`.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind clusters `boutique` (starting context) and `lab` (the `recette` context) |
| Duration | about 15 minutes |
| Related page | [Kubeconfig and contexts, Put into practice section](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-contexte/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-changer-de-contexte
dsoxlab check k8s-changer-de-contexte
```
