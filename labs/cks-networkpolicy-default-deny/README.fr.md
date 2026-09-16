# Tout interdire, puis rouvrir le strict nécessaire, DNS compris

Lab **CKS**, domaine *Cluster Setup* (15 % de l'épreuve), compétence « Use
Network security policies to restrict cluster level access ».

Le catalogue a déjà deux labs NetworkPolicy, un CKA et un CKAD, qui
apprennent à **autoriser** un flux. Celui-ci part de l'inverse, le modèle
zéro-confiance : on ferme tout, puis on rouvre. Le piège qu'il éprouve
n'existe que dans ce sens-là, et c'est le plus coûteux du domaine : **une
sortie fermée par défaut casse le DNS**, et rien ne le signale, ni dans les
events ni dans l'état des Pods.

Les Pods sont fournis par le setup. Ce n'est pas un raccourci : le sujet du
CKS est de fermer un namespace sans casser ce qui doit continuer, pas de créer
des Pods. `annuaire` sert d'instrument de mesure pour la sortie, et il écoute
vraiment : une requête vers un Pod qui n'écoute rien échoue de toute façon, et
un test bâti sur une telle cible serait vrai avant le travail.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 20 minutes |
| Leçon jumelée | [Network Policies](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/network-policies/) |

```bash
dsoxlab run   cks-networkpolicy-default-deny
dsoxlab check cks-networkpolicy-default-deny
```

Transposé de K8sExamLab le 2026-09-16, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
