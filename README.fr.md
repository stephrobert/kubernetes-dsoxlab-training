# Kubernetes DevSecOps Training : labs CKA, CKAD et CKS

**Langue :** [English](./README.md) · [Français](./README.fr.md)

[![CI](https://github.com/stephrobert/kubernetes-dsoxlab-training/actions/workflows/ci.yml/badge.svg)](https://github.com/stephrobert/kubernetes-dsoxlab-training/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://img.shields.io/ossf-scorecard/github.com/stephrobert/kubernetes-dsoxlab-training?label=OpenSSF%20Scorecard)](https://securityscorecards.dev/viewer/?uri=github.com/stephrobert/kubernetes-dsoxlab-training)
[![Conformité Plumber](https://score.getplumber.io/github.com/stephrobert/kubernetes-dsoxlab-training.svg)](https://score.getplumber.io/github.com/stephrobert/kubernetes-dsoxlab-training)
[![SLSA 3](https://slsa.dev/images/gh-badge-level3.svg)](https://slsa.dev)
[![Licence : CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](LICENSE)

Catalogue de **labs et de capstones vérifiables** pour la
[formation Kubernetes](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/)
du blog de Stéphane Robert. Joué par la CLI
[dsoxlab](https://github.com/stephrobert/dsoxlab).

Un **micro-lab** éprouve une compétence nommée par le blueprint et le dit dans
son titre. Un **capstone** n'en nomme aucune : il donne une situation, un seuil
de réussite à 66 % comme l'examen, et laisse choisir les outils.

**Les trois certifications Kubernetes sont entièrement pratiques.** Le candidat
répare ou construit sur un cluster réel : il ne reconnaît pas une bonne réponse
parmi quatre. Un quiz prépare au vocabulaire, pas à l'épreuve. Ce catalogue
donne à l'apprenant de quoi **prouver** qu'il sait faire.

Chaque lab pose un état initial, énonce un objectif, et valide en lisant
**l'état du système**, jamais les commandes tapées.

## Démarrer

```bash
uv tool install dsoxlab        # la CLI, outil externe

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

### Le parcours recommandé

C'est l'ordre dans lequel les labs sont faits pour être joués, tel que `meta.yml` le déclare. C'est une progression pédagogique, pas la structure de l'examen : elle va de ce dont un cluster est fait vers son diagnostic, et se termine par le capstone, qui suppose le reste joué. Le tableau plus bas répond à l'autre question, celle de la couverture : quel domaine du blueprint chaque lab éprouve.

**CKA, Certified Kubernetes Administrator**

1. [`cka-static-pod`](labs/cka-static-pod/) : Poser un Pod statique sur un worker, sans passer par l'API
2. [`cka-daemonset-all-nodes`](labs/cka-daemonset-all-nodes/) : Un agent sur chaque nœud, control plane compris
3. [`cka-rbac-serviceaccount`](labs/cka-rbac-serviceaccount/) : Donner une identité à une application : ServiceAccount, Role, RoleBinding
4. [`cka-taints-tolerations-placement`](labs/cka-taints-tolerations-placement/) : Réserver un nœud : taint, tolérance et nodeSelector
5. [`cka-node-affinity`](labs/cka-node-affinity/) : Placer avec nodeAffinity : contrainte obligatoire et préférence
6. [`cka-networkpolicy-isolate-db`](labs/cka-networkpolicy-isolate-db/) : Isoler la base de données : seul le backend y accède
7. [`cka-pv-pvc-storageclass`](labs/cka-pv-pvc-storageclass/) : Un volume persistant : PersistentVolume, PersistentVolumeClaim et un Pod qui écrit
8. [`cka-deployment-rollout-rollback`](labs/cka-deployment-rollout-rollback/) : Revenir en arrière sur un déploiement bloqué, puis livrer la bonne version
9. [`cka-node-drain-cordon`](labs/cka-node-drain-cordon/) : Vider un worker pour une maintenance, sans couper le service
10. [`cka-hpa-autoscaling`](labs/cka-hpa-autoscaling/) : Faire monter en charge automatiquement avec un HorizontalPodAutoscaler
11. [`cka-troubleshoot-imagepullbackoff`](labs/cka-troubleshoot-imagepullbackoff/) : Sortir un Pod de l'ImagePullBackOff
12. [`cka-troubleshoot-crashloopbackoff`](labs/cka-troubleshoot-crashloopbackoff/) : Sortir un Deployment du CrashLoopBackOff
13. [`cka-kubectl-debug`](labs/cka-kubectl-debug/) : Entrer dans un conteneur sans shell avec kubectl debug
14. [`cka-troubleshoot-dns`](labs/cka-troubleshoot-dns/) : Rétablir la résolution DNS du cluster
15. [`cka-troubleshoot-networking`](labs/cka-troubleshoot-networking/) : Rétablir le trafic vers un Service
16. [`cka-troubleshoot-node-notready`](labs/cka-troubleshoot-node-notready/) : Ramener un nœud NotReady dans le cluster
17. [`cka-troubleshoot-kubelet`](labs/cka-troubleshoot-kubelet/) : Réparer un kubelet qui refuse de démarrer
18. [`cka-troubleshoot-apiserver`](labs/cka-troubleshoot-apiserver/) : Remettre l'API server en service
19. [`cka-etcd-backup-restore`](labs/cka-etcd-backup-restore/) : Sauvegarder etcd, puis restaurer le cluster depuis un instantané
20. [`cka-capstone-portail`](labs/cka-capstone-portail/) : Capstone : remettre le portail en service, sans personne à qui demander · **capstone**

**CKAD, Certified Kubernetes Application Developer**

1. [`ckad-pod-resources-labels`](labs/ckad-pod-resources-labels/) : Un Pod à deux conteneurs, avec budgets, labels et annotation
2. [`ckad-configmap-secret-injection`](labs/ckad-configmap-secret-injection/) : Injecter configuration et secrets dans un Pod
3. [`ckad-probes-all-types`](labs/ckad-probes-all-types/) : Trois sondes sur un Pod : startup, liveness, readiness
4. [`ckad-init-container`](labs/ckad-init-container/) : Attendre une dépendance avec un init container
5. [`ckad-multi-container-sidecar`](labs/ckad-multi-container-sidecar/) : Un sidecar natif qui suit les logs de l'application
6. [`ckad-expose-service`](labs/ckad-expose-service/) : Exposer un Deployment par un Service ClusterIP
7. [`ckad-security-context-hardened`](labs/ckad-security-context-hardened/) : Durcir un Pod avec un securityContext
8. [`ckad-rbac-role-rolebinding`](labs/ckad-rbac-role-rolebinding/) : Donner un accès en lecture seule aux Pods avec RBAC
9. [`ckad-networkpolicy-ingress-egress`](labs/ckad-networkpolicy-ingress-egress/) : Cloisonner trois tiers avec des NetworkPolicy ingress et egress
10. [`ckad-rolling-update-strategy`](labs/ckad-rolling-update-strategy/) : Régler une mise à jour progressive : maxSurge et maxUnavailable
11. [`ckad-blue-green-deployment`](labs/ckad-blue-green-deployment/) : Basculer le trafic d'une version à l'autre : blue-green
12. [`ckad-kustomize-overlays`](labs/ckad-kustomize-overlays/) : Une base Kustomize et deux overlays, dev et prod
13. [`ckad-helm-install-upgrade`](labs/ckad-helm-install-upgrade/) : Installer, mettre à jour et revenir en arrière avec Helm 4
14. [`ckad-job-cronjob`](labs/ckad-job-cronjob/) : Un Job à complétions parallèles et un CronJob
15. [`ckad-in-place-pod-vertical-scaling`](labs/ckad-in-place-pod-vertical-scaling/) : Redimensionner un Pod en place, sans le redémarrer
16. [`ckad-troubleshoot-missing-configmap`](labs/ckad-troubleshoot-missing-configmap/) : Un Pod bloqué par un ConfigMap qui n'existe pas
17. [`ckad-troubleshoot-crashloop`](labs/ckad-troubleshoot-crashloop/) : Trois Pods en CrashLoopBackOff, trois causes
18. [`ckad-capstone-boutique`](labs/ckad-capstone-boutique/) : Capstone : livrer la boutique, à partir du seul cahier des charges · **capstone**

**CKS, Certified Kubernetes Security Specialist**

1. [`cks-apparmor-confiner-un-pod`](labs/cks-apparmor-confiner-un-pod/) : Confiner un Pod avec un profil AppArmor
2. [`cks-pod-security-admission`](labs/cks-pod-security-admission/) : Refuser un Pod privilégié à l'admission, avec Pod Security Admission
3. [`cks-image-pinned-digest`](labs/cks-image-pinned-digest/) : Épingler une image par son digest, et prouver que le tag ne suffit pas
4. [`cks-rbac-least-privilege`](labs/cks-rbac-least-privilege/) : Retirer cluster-admin à un compte de service, sans le priver de son travail

### La couverture du blueprint

Les mêmes labs, groupés par le domaine que l'examen nomme. C'est la vue qui répond à « qu'est-ce que je peux prouver ? », et elle n'est délibérément pas l'ordre dans lequel les jouer.

#### CKA, Certified Kubernetes Administrator

20 lab(s).

| Lab | Titre | Domaine du blueprint | Durée | Validé | Leçon jumelée |
|---|---|---|---|---|---|
| [`cka-etcd-backup-restore`](labs/cka-etcd-backup-restore/) | Sauvegarder etcd, puis restaurer le cluster depuis un instantané | cluster-architecture-installation-configuration | 25m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/etcd/) |
| [`cka-node-drain-cordon`](labs/cka-node-drain-cordon/) | Vider un worker pour une maintenance, sans couper le service | cluster-architecture-installation-configuration | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/preparer-maintenance-cluster-kubernetes/) |
| [`cka-rbac-serviceaccount`](labs/cka-rbac-serviceaccount/) | Donner une identité à une application : ServiceAccount, Role, RoleBinding | cluster-architecture-installation-configuration | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/serviceaccounts-developpeurs/) |
| [`cka-static-pod`](labs/cka-static-pod/) | Poser un Pod statique sur un worker, sans passer par l'API | cluster-architecture-installation-configuration | 10m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/worker-nodes/) |
| [`cka-networkpolicy-isolate-db`](labs/cka-networkpolicy-isolate-db/) | Isoler la base de données : seul le backend y accède | services-networking | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/network-policies/) |
| [`cka-pv-pvc-storageclass`](labs/cka-pv-pvc-storageclass/) | Un volume persistant : PersistentVolume, PersistentVolumeClaim et un Pod qui écrit | storage | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/storage/) |
| [`cka-kubectl-debug`](labs/cka-kubectl-debug/) | Entrer dans un conteneur sans shell avec kubectl debug | troubleshooting | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/debug-applications/) |
| [`cka-troubleshoot-apiserver`](labs/cka-troubleshoot-apiserver/) | Remettre l'API server en service | troubleshooting | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cluster-troubleshooting/) |
| [`cka-troubleshoot-crashloopbackoff`](labs/cka-troubleshoot-crashloopbackoff/) | Sortir un Deployment du CrashLoopBackOff | troubleshooting | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/crashloopbackoff-kubernetes/) |
| [`cka-troubleshoot-dns`](labs/cka-troubleshoot-dns/) | Rétablir la résolution DNS du cluster | troubleshooting | 10m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/coredns/) |
| [`cka-troubleshoot-imagepullbackoff`](labs/cka-troubleshoot-imagepullbackoff/) | Sortir un Pod de l'ImagePullBackOff | troubleshooting | 10m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/imagepullbackoff-kubernetes/) |
| [`cka-troubleshoot-kubelet`](labs/cka-troubleshoot-kubelet/) | Réparer un kubelet qui refuse de démarrer | troubleshooting | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cluster-troubleshooting/) |
| [`cka-troubleshoot-networking`](labs/cka-troubleshoot-networking/) | Rétablir le trafic vers un Service | troubleshooting | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/) |
| [`cka-troubleshoot-node-notready`](labs/cka-troubleshoot-node-notready/) | Ramener un nœud NotReady dans le cluster | troubleshooting | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cluster-troubleshooting/) |
| [`cka-daemonset-all-nodes`](labs/cka-daemonset-all-nodes/) | Un agent sur chaque nœud, control plane compris | workloads-scheduling | 10m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/daemonsets/) |
| [`cka-deployment-rollout-rollback`](labs/cka-deployment-rollout-rollback/) | Revenir en arrière sur un déploiement bloqué, puis livrer la bonne version | workloads-scheduling | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/deployments/) |
| [`cka-hpa-autoscaling`](labs/cka-hpa-autoscaling/) | Faire monter en charge automatiquement avec un HorizontalPodAutoscaler | workloads-scheduling | 20m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/horizontal-pod-scaling/) |
| [`cka-node-affinity`](labs/cka-node-affinity/) | Placer avec nodeAffinity : contrainte obligatoire et préférence | workloads-scheduling | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/affinity-toleration-taint/) |
| [`cka-taints-tolerations-placement`](labs/cka-taints-tolerations-placement/) | Réserver un nœud : taint, tolérance et nodeSelector | workloads-scheduling | 10m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/affinity-toleration-taint/) |
| [`cka-capstone-portail`](labs/cka-capstone-portail/) | Capstone : remettre le portail en service, sans personne à qui demander | capstone, plusieurs domaines | 45m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cluster-troubleshooting/) |

#### CKAD, Certified Kubernetes Application Developer

18 lab(s).

| Lab | Titre | Domaine du blueprint | Durée | Validé | Leçon jumelée |
|---|---|---|---|---|---|
| [`ckad-blue-green-deployment`](labs/ckad-blue-green-deployment/) | Basculer le trafic d'une version à l'autre : blue-green | application-deployment | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/) |
| [`ckad-helm-install-upgrade`](labs/ckad-helm-install-upgrade/) | Installer, mettre à jour et revenir en arrière avec Helm 4 | application-deployment | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/helm/install-releases/) |
| [`ckad-kustomize-overlays`](labs/ckad-kustomize-overlays/) | Une base Kustomize et deux overlays, dev et prod | application-deployment | 20m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/deployments/) |
| [`ckad-rolling-update-strategy`](labs/ckad-rolling-update-strategy/) | Régler une mise à jour progressive : maxSurge et maxUnavailable | application-deployment | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rolling-updates-rollbacks/) |
| [`ckad-init-container`](labs/ckad-init-container/) | Attendre une dépendance avec un init container | application-design | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/init-containers-sidecars/) |
| [`ckad-job-cronjob`](labs/ckad-job-cronjob/) | Un Job à complétions parallèles et un CronJob | application-design | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/jobs-cronjobs/) |
| [`ckad-multi-container-sidecar`](labs/ckad-multi-container-sidecar/) | Un sidecar natif qui suit les logs de l'application | application-design | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/init-containers-sidecars/) |
| [`ckad-pod-resources-labels`](labs/ckad-pod-resources-labels/) | Un Pod à deux conteneurs, avec budgets, labels et annotation | application-design | 10m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/requests-limits/) |
| [`ckad-configmap-secret-injection`](labs/ckad-configmap-secret-injection/) | Injecter configuration et secrets dans un Pod | application-environment | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/configmaps/) |
| [`ckad-in-place-pod-vertical-scaling`](labs/ckad-in-place-pod-vertical-scaling/) | Redimensionner un Pod en place, sans le redémarrer | application-environment | 10m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/requests-limits/) |
| [`ckad-rbac-role-rolebinding`](labs/ckad-rbac-role-rolebinding/) | Donner un accès en lecture seule aux Pods avec RBAC | application-environment | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rbac/) |
| [`ckad-security-context-hardened`](labs/ckad-security-context-hardened/) | Durcir un Pod avec un securityContext | application-environment | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/security-context/) |
| [`ckad-probes-all-types`](labs/ckad-probes-all-types/) | Trois sondes sur un Pod : startup, liveness, readiness | application-observability | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/probes/) |
| [`ckad-troubleshoot-crashloop`](labs/ckad-troubleshoot-crashloop/) | Trois Pods en CrashLoopBackOff, trois causes | application-observability | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/crashloopbackoff-kubernetes/) |
| [`ckad-troubleshoot-missing-configmap`](labs/ckad-troubleshoot-missing-configmap/) | Un Pod bloqué par un ConfigMap qui n'existe pas | application-observability | 10m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/debug-applications/) |
| [`ckad-expose-service`](labs/ckad-expose-service/) | Exposer un Deployment par un Service ClusterIP | services-networking | 10m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/) |
| [`ckad-networkpolicy-ingress-egress`](labs/ckad-networkpolicy-ingress-egress/) | Cloisonner trois tiers avec des NetworkPolicy ingress et egress | services-networking | 20m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/network-policies/) |
| [`ckad-capstone-boutique`](labs/ckad-capstone-boutique/) | Capstone : livrer la boutique, à partir du seul cahier des charges | capstone, plusieurs domaines | 45m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/deployments/) |

#### CKS, Certified Kubernetes Security Specialist

4 lab(s).

| Lab | Titre | Domaine du blueprint | Durée | Validé | Leçon jumelée |
|---|---|---|---|---|---|
| [`cks-rbac-least-privilege`](labs/cks-rbac-least-privilege/) | Retirer cluster-admin à un compte de service, sans le priver de son travail | cluster-hardening | 20m | 2026-09-16 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rbac/) |
| [`cks-pod-security-admission`](labs/cks-pod-security-admission/) | Refuser un Pod privilégié à l'admission, avec Pod Security Admission | minimize-vulnerabilities | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/pod-security-standards/) |
| [`cks-image-pinned-digest`](labs/cks-image-pinned-digest/) | Épingler une image par son digest, et prouver que le tag ne suffit pas | supply-chain-security | 15m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/supply-chain-security/) |
| [`cks-apparmor-confiner-un-pod`](labs/cks-apparmor-confiner-un-pod/) | Confiner un Pod avec un profil AppArmor | system-hardening | 25m | 2026-09-15 | [leçon](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/apparmor/) |

Total : **42 lab(s)**. La colonne « Validé » porte la date du dernier passage de `scripts/valider-labs.py`, qui joue le lab dans les deux sens et vérifie qu'il ne laisse aucune trace. Un lab livrable n'est pas un lab validé.

**Runtime validé : Kubernetes v1.37.0.** **Curriculum de référence : CKA v1.35, CKAD v1.35, CKS v1.34** ([cncf/curriculum](https://github.com/cncf/curriculum)). Les deux n'avancent pas à la même vitesse : les labs tournent sur un Kubernetes plus récent que le curriculum publié, et les annoncer séparément évite de laisser croire que l'examen porte sur la version du runtime.

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

Copyright (c) 2026 Stéphane Robert, https://blog.stephane-robert.info

Ce catalogue est publié sous licence
[Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE). Vous
pouvez le partager et l'adapter, y compris commercialement, à une condition :
créditer Stéphane Robert, lier le blog, et indiquer si vous avez modifié le
contenu, sans laisser entendre que l'auteur approuve votre usage.

Le fichier `LICENSE` ne contient que le texte officiel de la licence, sans
en-tête ajouté : c'est ce qui permet à GitHub de la reconnaître.
