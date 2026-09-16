# Signer une image, et prouver la signature en faisant refuser une autre

Lab **CKS**, domaine *Supply Chain Security* (20 % de l'épreuve), compétence
« Verify platform binaries before deploying » appliquée aux images.

Le registre est **local**, monté par le setup en `hostNetwork` sur le port
5000 du nœud. Ce n'est pas un raccourci : signer suppose de **pousser** la
signature à côté de l'image, dans le même dépôt, et aucun registre public ne
le permettrait sans identifiants. Un lab qui demanderait un compte Docker Hub
ne serait jouable par personne.

Le dernier test prend la clé publique du ConfigMap, comme le ferait un tiers,
et l'emploie sur les **deux** images. C'est le refus de l'image non signée qui
donne sa valeur à l'acceptation de l'autre : une vérification qui accepte tout
ressemble à une chaîne qui fonctionne.

Mesuré le 2026-09-16, et **cosign 3.x réserve deux pièges de version**.

Le premier : `--tlog-upload=false` n'est plus accepté et renvoie vers un
`--signing-config`. La signature contre un registre local fonctionne sans rien
désactiver, et c'est la voie que le lab emploie.

Le second est plus trompeur, parce que tous les articles sur le sujet disent
encore le contraire : le tag de la signature **n'est plus suffixé `.sig`**.
Le dépôt porte `sha256-<digest>` tout court. Une première version du test
cherchait `.sig`, ne trouvait rien, et déclarait qu'aucune signature n'avait
été poussée alors qu'elle était bien là.

cosign 3.1.3 et crane 0.22.1 sont posés par **mise**, depuis
`shared/outil-par-mise.yml`.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 30 minutes |
| Leçon jumelée | [Supply Chain Security](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/supply-chain-security/) |

```bash
dsoxlab run   cks-cosign-verify-image
dsoxlab check cks-cosign-verify-image
```

Le `cleanup.yaml` retire les clés du nœud : une clé privée laissée sur une
machine partagée est exactement ce que ce domaine apprend à ne pas faire.

Transposé de K8sExamLab le 2026-09-16, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
