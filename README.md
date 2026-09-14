# Kubernetes DevSecOps Training : labs CKA, CKAD et CKS

Catalogue de **micro-labs vérifiables** pour la
[formation Kubernetes](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/)
du blog de Stéphane Robert. Joué par la CLI [dsoxlab](https://github.com/stephrobert/dsoxlab).

**Les trois certifications Kubernetes sont entièrement pratiques.** Le candidat
répare ou construit sur un cluster réel : il ne reconnaît pas une bonne réponse
parmi quatre. Un quiz prépare au vocabulaire, pas à l'épreuve. Ce catalogue
donne à l'apprenant de quoi **prouver** qu'il sait faire.

Chaque lab pose un état initial, énonce un objectif, et valide en lisant
**l'état du système**, jamais les commandes tapées.

## Démarrer

```bash
git clone https://github.com/stephrobert/kubernetes-dsoxlab-training.git
cd kubernetes-dsoxlab-training
ansible-galaxy collection install -r requirements.yml

export LAB_HOME=$PWD
dsoxlab use --provider kvm
dsoxlab provision

dsoxlab list-labs
dsoxlab run   cks-apparmor-confiner-un-pod
dsoxlab check cks-apparmor-confiner-un-pod
```

`dsoxlab destroy` rend les machines.

## L'infrastructure : un cluster kubeadm vanilla

Deux VM Ubuntu 24.04, la distribution que recommande le guide kubeadm publié.
Le socle installe un cluster **Kubernetes 1.37**, la version qu'enseigne la
formation.

**Pourquoi pas kind ?** Parce que certains faits ne se prouvent pas dans un
conteneur. Sur un nœud kind, le kubelet refuse un Pod AppArmor avec
`Cannot enforce AppArmor: AppArmor is not enabled on the host`. La formation
enseigne sur kind, ce catalogue éprouve sur des machines.

## Contribuer

Les règles d'écriture d'un lab, les pièges de topologie et la doctrine de test
vivent dans [`CLAUDE.md`](CLAUDE.md). Le backlog est dans
[`todo/ROADMAP-LABS.md`](todo/ROADMAP-LABS.md).

Un lab n'est validé que joué dans les deux sens, et sans trace :

```bash
python3 scripts/valider-labs.py --lab <id>
```

Le validateur photographie le cluster, joue le lab, vérifie que les tests
rendent 0 avant le travail et 100 après la solution du formateur, nettoie,
rejoue, puis compare le cluster à sa photographie. Le résultat de chaque lab,
date et version de Kubernetes comprises, est dans
[`validation-labs.json`](validation-labs.json).

## Transposer les labs hérités

61 labs CKA/CKAD/CKS existent dans `~/Projets/K8sExamLab`, l'ancêtre archivé de
dsoxlab. Leur substance est récupérable et l'outillage est là :

```bash
python3 scripts/convertir-k8sexamlab.py --lab <chemin>   # transpose
python3 scripts/proposer-doc-url.py                      # jumelle la leçon
python3 scripts/check-labs-completude.py --check         # ce qui reste
```

La transposition est mécanique ; la **validation ne l'est pas**. Un lab
transposé qui passe la structure ne prouve rien : le premier essai a révélé une
solution héritée qui contredisait son propre setup.

## Licence

Copyright (c) 2026 Stéphane Robert, https://blog.stephane-robert.info

Ce catalogue est publié sous licence
[Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE). Vous
pouvez le partager et l'adapter, y compris commercialement, à une condition :
créditer Stéphane Robert, lier le blog, et indiquer si vous avez modifié le
contenu, sans laisser entendre que l'auteur approuve votre usage.

Le fichier `LICENSE` ne contient que le texte officiel de la licence, sans
en-tête ajouté : c'est ce qui permet à GitHub de la reconnaître.
