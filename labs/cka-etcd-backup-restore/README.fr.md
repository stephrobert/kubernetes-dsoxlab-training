# Sauvegarder etcd, puis restaurer le cluster depuis un instantané

Lab **CKA**, domaine *Cluster Architecture, Installation and Configuration*
(25 % de l'épreuve), compétence « Perform etcd backup and restore ».

Ce lab existe parce que la formation **ne peut pas le prouver sur kind** : y
restaurer etcd coûte le cluster. La vague 1 du backlog le réclamait sous le
nom `cka-restaurer-etcd`, avec cette note : « la restauration n'a pas été
jouée ». Elle l'est ici, et le jouer a montré que la procédure enseignée
arrêtait le kubelet, ce qui n'arrête pas etcd. La leçon a été corrigée.

Le lab hérité faisait supprimer le namespace par le candidat et vérifiait
l'instantané avec `etcdctl snapshot status`, commande qui n'existe plus en
etcd 3.7 et rend pourtant 0. Ici la perte a déjà eu lieu, une sauvegarde de
la veille existe, et les tests prouvent la restauration par la date du
répertoire de données en service, les UID des objets revenus, et la
disparition d'un objet écrit après la sauvegarde. L'identité du membre etcd
n'y sert pas : mesurée identique avant et après restauration, puisque etcd
la calcule à partir des URL de pair et du jeton de cluster.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 25 minutes |
| Leçon jumelée | [etcd : la base clé/valeur du control plane](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/etcd/) |

```bash
dsoxlab run   cka-etcd-backup-restore
dsoxlab check cka-etcd-backup-restore
```

Le nettoyage ramène etcd sur `/var/lib/etcd` avec le manifeste d'origine, en
gardant les données courantes, et repart d'un instantané de secours si le
candidat a cassé le cluster.

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
