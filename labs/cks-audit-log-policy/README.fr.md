# Enregistrer qui lit les Secrets, et seulement les métadonnées du reste

Lab **CKS**, domaine *Monitoring, Logging and Runtime Security* (20 % de
l'épreuve). Ce domaine pèse un cinquième de l'examen et n'avait aucun lab.

Ce lab modifie le **manifeste statique du kube-apiserver**, ce qu'un cluster
en conteneur ne permet pas de faire proprement : c'est une des raisons d'être
des VM de ce catalogue.

Le dernier test ne lit pas la politique, il lit le **journal que le cluster
vient d'écrire**. Une politique posée sur le disque ne prouve rien : le
fichier peut être mal formé, les flags manquer, les volumes ne pas être
montés, et l'API server tourner quand même sans écrire une ligne. Il exige
aussi les deux niveaux : une politique qui enregistrerait tout en
`RequestResponse` recopierait chaque Secret en clair dans le journal, et
échoue ici.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 25 minutes |
| Leçon jumelée | [Audit Logs](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/audit-logs/) |

```bash
dsoxlab run   cks-audit-log-policy
dsoxlab check cks-audit-log-policy
```

Le setup sauvegarde le manifeste d'origine dans `/var/backups`, **jamais**
dans `/etc/kubernetes/manifests` : le kubelet y lancerait la copie comme un
second Pod statique, et deux API servers se disputeraient le même port. Le
cleanup restaure depuis cette sauvegarde, puis attend que l'API réponde.

Transposé de K8sExamLab le 2026-09-16, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
