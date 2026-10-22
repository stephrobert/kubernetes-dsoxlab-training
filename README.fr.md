# Kubernetes DevSecOps Training : labs CKA, CKAD et CKS

**Langue :** [English](./README.md) · [Français](./README.fr.md)

[![CI](https://github.com/stephrobert/kubernetes-dsoxlab-training/actions/workflows/ci.yml/badge.svg)](https://github.com/stephrobert/kubernetes-dsoxlab-training/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://img.shields.io/ossf-scorecard/github.com/stephrobert/kubernetes-dsoxlab-training?label=OpenSSF%20Scorecard)](https://securityscorecards.dev/viewer/?uri=github.com/stephrobert/kubernetes-dsoxlab-training)
[![Conformité Plumber](https://score.getplumber.io/github.com/stephrobert/kubernetes-dsoxlab-training.svg)](https://score.getplumber.io/github.com/stephrobert/kubernetes-dsoxlab-training)
[![SLSA 3](https://slsa.dev/images/gh-badge-level3.svg)](https://slsa.dev)
[![Licence : CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](LICENSE)

Catalogue de **labs et de capstones vérifiables** pour la
[formation Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/)
du blog de Stéphane Robert. Joué par la CLI
[dsoxlab](https://github.com/stephrobert/dsoxlab).

## Ce que c'est

Un **micro-lab** exerce une compétence nommée par le blueprint, et le dit dans
son titre. Un **capstone** n'en nomme aucune : il remet une situation, un seuil
de réussite de 66 % comme à l'examen, et laisse choisir les outils.

**Les trois certifications Kubernetes sont entièrement pratiques.** Le candidat
répare ou construit sur un vrai cluster : il ne choisit pas la bonne réponse
parmi quatre. Un quiz prépare au vocabulaire, pas à l'examen. Ce catalogue
donne à l'apprenant les moyens de **prouver** qu'il sait faire.

Chaque lab pose un état initial, énonce un objectif, et valide en lisant
**l'état du système**, jamais les commandes tapées.

## Prérequis

- **Python 3.11+ et [`uv`](https://docs.astral.sh/uv/)**
- **`git`**
- **Un hyperviseur**, puisque tous les labs d'ici sont `runtime: vm` : soit
  **libvirt/KVM** (avec `terraform` et le provider `dmacvicar/libvirt`), soit
  **Incus**. Le provider est déclaré en liste dans [`meta.yml`](meta.yml), et
  **une liste ne se résout pas d'elle-même** : choisissez-en un avec
  `dsoxlab use --provider kvm`.
- **Environ 7 Go de RAM libre et 45 Go de disque** pour les deux machines, et
  la section suivante dit pourquoi il y en a deux.
- **Les collections Ansible** de [`requirements.yml`](requirements.yml), dont
  les versions sont **bornées à dessein** : celles qui ont validé le catalogue,
  pas les dernières publiées.
- **Un accès réseau sortant** au premier provision, pour récupérer l'image de
  base et les paquets Kubernetes.

`dsoxlab doctor` dit ce dont ce dépôt a besoin et ce dont il n'a pas besoin, et
distingue un contrôle qui a échoué d'un contrôle qu'il n'a pas pu mesurer.

## Installation

`dsoxlab` est publié sur [PyPI](https://pypi.org/project/dsoxlab/).
Installez-le en outil autonome, pour qu'il reste hors de ce dépôt :

```bash
# 1. La CLI dsoxlab (outil externe, hors de ce dépôt)
uv tool install dsoxlab

# 2. Ce catalogue de labs
git clone https://github.com/stephrobert/kubernetes-dsoxlab-training.git
cd kubernetes-dsoxlab-training

# 3. Les collections Ansible, aux versions bornées
ansible-galaxy collection install -r requirements.yml

# 4. Vérifier le contrat et la machine
dsoxlab validate-structure
dsoxlab doctor
```

### Votre premier lab, en cinq minutes

Le cluster doit exister d'abord : rien ici ne tourne sur votre propre poste.

```bash
export LAB_HOME=$PWD
dsoxlab use --provider kvm           # une liste de providers ne se résout pas seule
dsoxlab provision                    # crée les deux machines et le cluster

dsoxlab list-labs
dsoxlab run       cks-apparmor-confiner-un-pod
dsoxlab challenge cks-apparmor-confiner-un-pod
dsoxlab check     cks-apparmor-confiner-un-pod

dsoxlab destroy                             # rend les machines
```

`provision` sort en code non nul si un hôte ne répond pas, et nomme les
domaines orphelins qu'il a laissés plutôt que d'annoncer un succès. Un `check`
joué sur un lab jamais démarré ne mesure rien, et le dit au lieu d'enregistrer
un 0.

### Garder à jour

```bash
uv tool upgrade dsoxlab        # le moteur, publié sur PyPI
git -C <ce dépôt> pull         # le catalogue
```

Le moteur et le catalogue avancent indépendamment : un nouveau `dsoxlab` ne
demande jamais de recloner les labs, et de nouveaux labs ne demandent jamais de
mettre l'outil à jour, tant que la version du contrat correspond.

## Comment ça marche

### Le contrat déclaratif, à deux niveaux

Le catalogue est décrit par des données, pas par du code, et c'est ce qui garde
le moteur `dsoxlab` indépendant du domaine :

- **`meta.yml`** à la racine déclare l'identité du dépôt, l'**infrastructure**
  (provider, réseau `lab-k8s`, `10.10.50.0/24`, et les deux hôtes avec leurs
  rôles) et l'**ordre** des sections affichées par `list-labs` ;
- **`lab.yaml`** par lab déclare ses `skills`, son `level`, son `runtime` (type
  et targets), ses `distros`, son `doc_url`, ses `certification_tags` et un
  bloc `validation`. Un `lab.fr.yaml` surcharge `title` et `description` en
  français, et rien d'autre.

Les gabarits Terraform et cloud-init sont **packagés dans dsoxlab**, pas ici :
ce dépôt ne déclare que son bloc `infra:` et sa clé publique dans `ssh/`.

### Le cycle de vie d'un lab

```bash
dsoxlab list-labs              # parcourir le catalogue
dsoxlab show      <id>         # métadonnées et état d'un lab
dsoxlab run       <id>         # poser l'état de départ
dsoxlab challenge <id>         # lire la mission, sans pas-à-pas
dsoxlab hint      <id>         # révéler un indice (déduit du score)
dsoxlab check     <id>         # lancer les tests, calculer et enregistrer le score
dsoxlab clean     <id>         # défaire ce que le lab a posé
dsoxlab progress               # avancement par section, score moyen
```

### Les runtimes

| Runtime | Ce que le lab demande |
|---|---|
| `vm` | les deux machines provisionnées par `dsoxlab provision`, avec le cluster kubeadm déjà debout. Les tests interrogent le serveur d'API et entrent dans les nœuds. |

Tous les labs sont `vm`, et aucun ne déclare `runtime.services` : le cluster
est le sujet, donc il vit dans les machines et non sur votre poste.

### Le modèle de validation

La validation **prouve l'état, elle ne fait pas confiance à l'apprenant**. Les
tests demandent au serveur d'API et aux nœuds ce qu'ils contiennent vraiment,
et un lab est prouvé **dans les deux sens** : les tests doivent échouer avant
le travail et passer après la solution du formateur. Un test vert avant le
travail n'est pas un test, c'est une hypothèse sur le setup.

`scripts/valider-labs.py` joue ce cycle entier : il photographie le cluster,
joue le lab, contrôle 0 avant et 100 après, nettoie, rejoue, puis compare le
cluster à sa photographie. **Un namespace oublié rend le lab ROUGE**, et c'est
voulu : ce n'est pas ce lab-là qui en paierait le prix, c'est le suivant. Le
résultat de chaque lab, avec sa date et sa version de Kubernetes, est dans
[`validation-labs.json`](validation-labs.json).

### Score, indices, avancement

`check` enregistre un score (tests réussis sur total, moins le coût des indices
révélés). Les indices sont **en base64** dans `challenge/hints.yaml`, pour qu'on
n'y accède pas en ouvrant le fichier, et leur coût croît avec leur précision.
L'historique vit dans une base SQLite **locale à ce dépôt**.

Un capstone déclare un **seuil de 66 %**, comme à l'examen, et `submit` traduit
la note en verdict. Une exécution qui n'a rien mesuré n'est ni une réussite ni
un échec : si tous les tests collectés skippent, `check` n'enregistre aucune
note et dit pourquoi. Un 0 accuserait le lab de ce qui manque au cluster, qui
est ici le plus souvent le cluster non provisionné.

### L'infrastructure : un cluster kubeadm vanilla

Deux VM Ubuntu 24.04, la distribution que recommande le guide kubeadm publié :
un control plane, `k8s-cp.lab`, et un worker, `k8s-w1.lab`, joignable par `ssh`
depuis le control plane comme à l'examen. Le socle installe un cluster
**Kubernetes 1.37**, la version qu'enseigne la formation, avec Calico comme CNI.

**Pourquoi pas kind ?** Parce que certains faits ne se prouvent pas dans un
conteneur. Sur un nœud kind, le kubelet refuse un Pod AppArmor avec
`Cannot enforce AppArmor: AppArmor is not enabled on the host`. La formation
enseigne sur kind, ce catalogue éprouve sur des machines.

## Le catalogue

<!-- LABS:START -->

Un tableau par examen, dans l'ordre que `meta.yml` déclare. Cet ordre est une progression pédagogique, pas la structure de l'examen : il va de ce dont un cluster est fait vers son diagnostic, et se termine par le capstone, qui suppose le reste joué. La colonne « Domaine du blueprint » répond à l'autre question, celle de la couverture : ce que chaque lab permet de prouver.

### CKA, Certified Kubernetes Administrator

Cinq domaines. Le troubleshooting pèse 30 %, plus que tout autre, et c'est celui qui sépare ceux qui connaissent Kubernetes de ceux qui savent l'exploiter.

25 lab(s).

| # | Lab | Titre | Domaine du blueprint | Durée | Validé | Leçon jumelée |
|---|---|---|---|---|---|---|
| 1 | [`cka-static-pod`](labs/cka-static-pod/) | Poser un Pod statique sur un worker, sans passer par l'API | cluster-architecture-installation-configuration | 10m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/worker-nodes/) |
| 2 | [`cka-daemonset-all-nodes`](labs/cka-daemonset-all-nodes/) | Un agent sur chaque nœud, control plane compris | workloads-scheduling | 10m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/daemonsets/) |
| 3 | [`cka-rbac-serviceaccount`](labs/cka-rbac-serviceaccount/) | Donner une identité à une application : ServiceAccount, Role, RoleBinding | cluster-architecture-installation-configuration | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/serviceaccounts-developpeurs/) |
| 4 | [`cka-taints-tolerations-placement`](labs/cka-taints-tolerations-placement/) | Réserver un nœud : taint, tolérance et nodeSelector | workloads-scheduling | 10m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/affinity-toleration-taint/) |
| 5 | [`cka-node-affinity`](labs/cka-node-affinity/) | Placer avec nodeAffinity : contrainte obligatoire et préférence | workloads-scheduling | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/affinity-toleration-taint/) |
| 6 | [`cka-networkpolicy-isolate-db`](labs/cka-networkpolicy-isolate-db/) | Isoler la base de données : seul le backend y accède | services-networking | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/network-policies/) |
| 7 | [`cka-ingress-path-routing`](labs/cka-ingress-path-routing/) | Router deux applications sur un seul hôte, et prouver que chacune reçoit la sienne | services-networking | 20m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/ingress/) |
| 8 | [`cka-gateway-api-httproute`](labs/cka-gateway-api-httproute/) | Router avec la Gateway API, et voir la Gateway se déclarer programmée | services-networking | 25m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/gateway-api/) |
| 9 | [`cka-pv-pvc-storageclass`](labs/cka-pv-pvc-storageclass/) | Un volume persistant : PersistentVolume, PersistentVolumeClaim et un Pod qui écrit | storage | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/storage/) |
| 10 | [`cka-storageclass-provisionnement-dynamique`](labs/cka-storageclass-provisionnement-dynamique/) | Obtenir un volume sans qu'un administrateur l'ait créé, et voir ce qu'il devient | storage | 25m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/storageclass/) |
| 11 | [`cka-deployment-rollout-rollback`](labs/cka-deployment-rollout-rollback/) | Revenir en arrière sur un déploiement bloqué, puis livrer la bonne version | workloads-scheduling | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/deployments/) |
| 12 | [`cka-node-drain-cordon`](labs/cka-node-drain-cordon/) | Vider un worker pour une maintenance, sans couper le service | cluster-architecture-installation-configuration | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/preparer-maintenance-cluster-kubernetes/) |
| 13 | [`cka-hpa-autoscaling`](labs/cka-hpa-autoscaling/) | Faire monter en charge automatiquement avec un HorizontalPodAutoscaler | workloads-scheduling | 20m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/horizontal-pod-scaling/) |
| 14 | [`cka-resourcequota-limitrange`](labs/cka-resourcequota-limitrange/) | Plafonner un namespace sans bloquer ceux qui oublient de se déclarer | workloads-scheduling | 25m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/resource-quotas/) |
| 15 | [`cka-troubleshoot-imagepullbackoff`](labs/cka-troubleshoot-imagepullbackoff/) | Sortir un Pod de l'ImagePullBackOff | troubleshooting | 10m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/imagepullbackoff-kubernetes/) |
| 16 | [`cka-troubleshoot-crashloopbackoff`](labs/cka-troubleshoot-crashloopbackoff/) | Sortir un Deployment du CrashLoopBackOff | troubleshooting | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/crashloopbackoff-kubernetes/) |
| 17 | [`cka-kubectl-debug`](labs/cka-kubectl-debug/) | Entrer dans un conteneur sans shell avec kubectl debug | troubleshooting | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/debug-applications/) |
| 18 | [`cka-troubleshoot-dns`](labs/cka-troubleshoot-dns/) | Rétablir la résolution DNS du cluster | troubleshooting | 10m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/coredns/) |
| 19 | [`cka-troubleshoot-networking`](labs/cka-troubleshoot-networking/) | Rétablir le trafic vers un Service | troubleshooting | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/) |
| 20 | [`cka-troubleshoot-node-notready`](labs/cka-troubleshoot-node-notready/) | Ramener un nœud NotReady dans le cluster | troubleshooting | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cluster-troubleshooting/) |
| 21 | [`cka-troubleshoot-kubelet`](labs/cka-troubleshoot-kubelet/) | Réparer un kubelet qui refuse de démarrer | troubleshooting | 15m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/worker-nodes/) |
| 22 | [`cka-troubleshoot-apiserver`](labs/cka-troubleshoot-apiserver/) | Remettre l'API server en service | troubleshooting | 15m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/control-plan/) |
| 23 | [`cka-etcd-backup-restore`](labs/cka-etcd-backup-restore/) | Sauvegarder etcd, puis restaurer le cluster depuis un instantané | cluster-architecture-installation-configuration | 25m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/etcd/) |
| 24 | [`cka-kubeadm-upgrade`](labs/cka-kubeadm-upgrade/) | Monter un cluster d'une version mineure, sans interrompre ce qui tourne | cluster-architecture | 40m | 2026-10-15 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/mettre-a-jour-cluster-kubernetes/) |
| 25 | [`cka-capstone-portail`](labs/cka-capstone-portail/) | Capstone : remettre le portail en service, sans personne à qui demander | capstone, plusieurs domaines | 45m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/certifications/cka/exercices/) |

### CKAD, Certified Kubernetes Application Developer

Cinq domaines orientés application. « Application Environment, Configuration and Security » pèse 25 %, le plus lourd des cinq.

20 lab(s).

| # | Lab | Titre | Domaine du blueprint | Durée | Validé | Leçon jumelée |
|---|---|---|---|---|---|---|
| 1 | [`ckad-pod-resources-labels`](labs/ckad-pod-resources-labels/) | Un Pod à deux conteneurs, avec budgets, labels et annotation | application-design | 10m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/requests-limits/) |
| 2 | [`ckad-configmap-secret-injection`](labs/ckad-configmap-secret-injection/) | Injecter configuration et secrets dans un Pod | application-environment | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/secrets/) |
| 3 | [`ckad-secret-injection-protection`](labs/ckad-secret-injection-protection/) | Sortir un mot de passe d'un manifeste, sans que l'application s'en aperçoive | application-environment | 20m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/secrets/) |
| 4 | [`ckad-probes-all-types`](labs/ckad-probes-all-types/) | Trois sondes sur un Pod : startup, liveness, readiness | application-observability | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/probes/) |
| 5 | [`ckad-init-container`](labs/ckad-init-container/) | Attendre une dépendance avec un init container | application-design | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/init-containers-sidecars/) |
| 6 | [`ckad-multi-container-sidecar`](labs/ckad-multi-container-sidecar/) | Un sidecar natif qui suit les logs de l'application | application-design | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/init-containers-sidecars/) |
| 7 | [`ckad-volumes-partage-entre-conteneurs`](labs/ckad-volumes-partage-entre-conteneurs/) | Faire lire à un conteneur ce qu'un autre écrit, et pas le reste | application-design | 20m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/volumes-applicatifs/) |
| 8 | [`ckad-expose-service`](labs/ckad-expose-service/) | Exposer un Deployment par un Service ClusterIP | services-networking | 10m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/) |
| 9 | [`ckad-security-context-hardened`](labs/ckad-security-context-hardened/) | Durcir un Pod avec un securityContext | application-environment | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/security-context/) |
| 10 | [`ckad-rbac-role-rolebinding`](labs/ckad-rbac-role-rolebinding/) | Donner un accès en lecture seule aux Pods avec RBAC | application-environment | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rbac/) |
| 11 | [`ckad-networkpolicy-ingress-egress`](labs/ckad-networkpolicy-ingress-egress/) | Cloisonner trois tiers avec des NetworkPolicy ingress et egress | services-networking | 20m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/network-policies/) |
| 12 | [`ckad-rolling-update-strategy`](labs/ckad-rolling-update-strategy/) | Régler une mise à jour progressive : maxSurge et maxUnavailable | application-deployment | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rolling-updates-rollbacks/) |
| 13 | [`ckad-blue-green-deployment`](labs/ckad-blue-green-deployment/) | Basculer le trafic d'une version à l'autre : blue-green | application-deployment | 15m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rolling-updates-rollbacks/) |
| 14 | [`ckad-kustomize-overlays`](labs/ckad-kustomize-overlays/) | Une base Kustomize et deux overlays, dev et prod | application-deployment | 20m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kustomize/) |
| 15 | [`ckad-helm-install-upgrade`](labs/ckad-helm-install-upgrade/) | Installer, mettre à jour et revenir en arrière avec Helm 4 | application-deployment | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/helm/install-releases/) |
| 16 | [`ckad-job-cronjob`](labs/ckad-job-cronjob/) | Un Job à complétions parallèles et un CronJob | application-design | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/jobs-cronjobs/) |
| 17 | [`ckad-in-place-pod-vertical-scaling`](labs/ckad-in-place-pod-vertical-scaling/) | Redimensionner un Pod en place, sans le redémarrer | application-environment | 10m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/requests-limits/) |
| 18 | [`ckad-troubleshoot-missing-configmap`](labs/ckad-troubleshoot-missing-configmap/) | Un Pod bloqué par un ConfigMap qui n'existe pas | application-observability | 10m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/debug-applications/) |
| 19 | [`ckad-troubleshoot-crashloop`](labs/ckad-troubleshoot-crashloop/) | Trois Pods en CrashLoopBackOff, trois causes | application-observability | 15m | 2026-09-16 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/crashloopbackoff-kubernetes/) |
| 20 | [`ckad-capstone-boutique`](labs/ckad-capstone-boutique/) | Capstone : livrer la boutique, à partir du seul cahier des charges | capstone, plusieurs domaines | 45m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/certifications/ckad/exercices/) |

### CKS, Certified Kubernetes Security Specialist

Six domaines. Trois d'entre eux pèsent 20 % chacun, soit 60 % à eux seuls. Plusieurs compétences y sont invérifiables sur un cluster en conteneur, ce qui est la raison d'être des VM de ce catalogue.

19 lab(s).

| # | Lab | Titre | Domaine du blueprint | Durée | Validé | Leçon jumelée |
|---|---|---|---|---|---|---|
| 1 | [`cks-apparmor-confiner-un-pod`](labs/cks-apparmor-confiner-un-pod/) | Confiner un Pod avec un profil AppArmor | system-hardening | 25m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/apparmor/) |
| 2 | [`cks-seccomp-profile`](labs/cks-seccomp-profile/) | Interdire un appel système à un conteneur, et le prouver de l'intérieur | system-hardening | 25m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/seccomp/) |
| 3 | [`cks-pod-security-admission`](labs/cks-pod-security-admission/) | Refuser un Pod privilégié à l'admission, avec Pod Security Admission | minimize-vulnerabilities | 15m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/pod-security-standards/) |
| 4 | [`cks-secure-existing-pod`](labs/cks-secure-existing-pod/) | Reprendre un Pod privilégié en production, sans le priver de son travail | minimize-vulnerabilities | 20m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/security-context/) |
| 5 | [`cks-security-context-immutable`](labs/cks-security-context-immutable/) | Rendre un conteneur immuable sans le faire tomber | minimize-vulnerabilities | 20m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/security-context/) |
| 6 | [`cks-runtime-sandbox-gvisor`](labs/cks-runtime-sandbox-gvisor/) | Isoler un Pod du noyau de l'hôte, et le prouver en lisant sa version | minimize-vulnerabilities | 25m | 2026-10-15 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/runtime-sandboxes/) |
| 7 | [`cks-image-pinned-digest`](labs/cks-image-pinned-digest/) | Épingler une image par son digest, et prouver que le tag ne suffit pas | supply-chain-security | 15m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/supply-chain-security/) |
| 8 | [`cks-validating-admission-policy`](labs/cks-validating-admission-policy/) | Faire refuser une image non épinglée par le cluster lui-même, sans webhook | supply-chain-security | 30m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/validating-admission-policy/) |
| 9 | [`cks-image-scanning-trivy`](labs/cks-image-scanning-trivy/) | Remplacer une image criblée de failles, et le prouver par un second scan | supply-chain-security | 25m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/image-scanning/) |
| 10 | [`cks-cosign-verify-image`](labs/cks-cosign-verify-image/) | Signer une image, et prouver la signature en faisant refuser une autre | supply-chain-security | 30m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/supply-chain-security/) |
| 11 | [`cks-dockerfile-static-analysis`](labs/cks-dockerfile-static-analysis/) | Corriger un Dockerfile que l'analyse statique refuse, sans changer l'application | supply-chain-security | 20m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/supply-chain-security/) |
| 12 | [`cks-rbac-least-privilege`](labs/cks-rbac-least-privilege/) | Retirer cluster-admin à un compte de service, sans le priver de son travail | cluster-hardening | 20m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rbac/) |
| 13 | [`cks-api-server-hardening`](labs/cks-api-server-hardening/) | Fermer le profileur de l'API server, sans fermer l'API | cluster-hardening | 25m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/cis-benchmark/) |
| 14 | [`cks-audit-log-policy`](labs/cks-audit-log-policy/) | Enregistrer qui lit les Secrets, et seulement les métadonnées du reste | monitoring-logging | 25m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/audit-logs/) |
| 15 | [`cks-networkpolicy-default-deny`](labs/cks-networkpolicy-default-deny/) | Tout interdire, puis rouvrir le strict nécessaire, DNS compris | cluster-setup | 20m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/network-policies/) |
| 16 | [`cks-istio-mtls-lockdown`](labs/cks-istio-mtls-lockdown/) | Exiger le mTLS dans un maillage, et le prouver par un client qui reste dehors | monitoring-logging | 30m | 2026-10-15 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/mtls-pod-to-pod/) |
| 17 | [`cks-ingress-tls`](labs/cks-ingress-tls/) | Servir un site en HTTPS avec son propre certificat, et non celui du contrôleur | cluster-setup | 25m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/ingress/) |
| 18 | [`cks-cis-benchmark-remediate`](labs/cks-cis-benchmark-remediate/) | Faire baisser le compte d'un audit CIS, et le prouver par un second audit | cluster-setup | 30m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/cis-benchmark/) |
| 19 | [`cks-capstone-enclave`](labs/cks-capstone-enclave/) | Capstone : ouvrir une enclave pour une équipe qui n'est pas de confiance | capstone, plusieurs domaines | 45m | 2026-10-12 | [leçon](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/certifications/cks/exercices/) |

Total : **64 lab(s)**. La colonne « Validé » porte la date du dernier passage de `scripts/valider-labs.py`, qui joue le lab dans les deux sens et vérifie qu'il ne laisse aucune trace. Un lab livrable n'est pas un lab validé.

**Runtime validé : Kubernetes v1.37.0, v1.37.1.** **Curriculum de référence : CKA v1.35, CKAD v1.35, CKS v1.34** ([cncf/curriculum](https://github.com/cncf/curriculum)). Les deux n'avancent pas à la même vitesse : les labs tournent sur un Kubernetes plus récent que le curriculum publié, et les annoncer séparément évite de laisser croire que l'examen porte sur la version du runtime.

<!-- LABS:END -->

## Contribuer

Les règles d'écriture d'un lab, la doctrine de test et les pièges du dépôt
vivent dans [`CONTRIBUTING.md`](CONTRIBUTING.md).

Un lab n'est validé que joué **dans les deux sens**, et sans trace :

```bash
python3 scripts/valider-labs.py --lab <id>
```

Le validateur photographie le cluster, joue le lab, vérifie que les tests
rendent 0 avant le travail et 100 après la solution du formateur, nettoie,
rejoue, puis compare le cluster à sa photographie. Un namespace oublié rend le
lab ROUGE : ce n'est pas lui qui en paierait le prix, c'est le lab suivant. Le
résultat de chaque lab, date et version de Kubernetes comprises, est dans
[`validation-labs.json`](validation-labs.json).

## Ce que la confrontation au cluster a corrigé dans les leçons

Chaque lab est jumelé à une leçon du blog, et l'écrire oblige à jouer ce que la
leçon affirme. Quatre erreurs y ont été relevées et corrigées, dont deux qui
rendaient une procédure inopérante :

- la procédure de restauration d'etcd arrêtait le kubelet, ce qui n'arrête pas
  le conteneur etcd : rien n'était restauré ;
- une restauration etcd ne change pas l'identité du membre sur un cluster
  kubeadm, contrairement à ce qui était écrit, parce qu'elle se recalcule à
  partir des URL de pair et du jeton de cluster.

La formation enseigne, ce catalogue éprouve : ce qu'il contredit remonte au
blog.

## Licence

Copyright (c) 2026 Stéphane Robert, https://www.stephane-robert.info

Ce catalogue est publié sous licence
[Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE). Vous
pouvez le partager et l'adapter, y compris commercialement, à une condition :
créditer Stéphane Robert, lier le blog, et indiquer si vous avez modifié le
contenu, sans laisser entendre que l'auteur approuve votre usage.

Le fichier `LICENSE` ne contient que le texte officiel de la licence, sans
en-tête ajouté : c'est ce qui permet à GitHub de la reconnaître.
