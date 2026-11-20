# Inspecter une release Helm en échec et la restaurer

**Helm** installe une application à partir d'un **chart**, un paquet de
manifestes paramétrables. Chaque installation s'appelle une **release**, et
chaque modification de la release crée une nouvelle **révision**. La leçon
montre comment chercher un chart, installer, décrire, revenir en arrière et
tester. Ce cours va plus loin : filtrer les versions d'un chart, voir ce
qu'une version change, comparer deux révisions, laisser Helm revenir en
arrière tout seul, et tomber dans le piège d'un retour arrière sans numéro.

Vous travaillez avec une release d'essai, `atelier`, dans un namespace
d'essai, `essai-helm`. Le challenge porte sur une autre release, déjà en échec
dans un autre namespace : vous la réparerez seul, à la fin.

Page associée : [La commande helm](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/helm/commande-helm/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-inspecter-et-restaurer-une-release-helm
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà, et le lab a installé
Helm.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026, avec Kubernetes v1.37.2 et Helm 4.3.2.

## 📚 Exercice 1 : chercher, puis filtrer les versions

Vérifiez la version de Helm et les dépôts de charts déclarés, puis cherchez le
chart `podinfo` :

```bash
helm version --short; helm repo list
helm search repo podinfo/podinfo
```

```text
v4.3.2+g8346aaa
NAME   	URL
podinfo	https://stefanprodan.github.io/podinfo
NAME           	CHART VERSION	APP VERSION	DESCRIPTION
podinfo/podinfo	6.17.0       	6.17.0     	Podinfo Helm chart for Kubernetes
```

Par défaut, `helm search repo` ne montre que la dernière version de toutes.
`--versions` les liste, de la plus récente à la plus ancienne (`head` garde les
premières lignes) :

```bash
helm search repo podinfo/podinfo --versions | head -4
```

```text
NAME           	CHART VERSION	APP VERSION	DESCRIPTION
podinfo/podinfo	6.17.0       	6.17.0     	Podinfo Helm chart for Kubernetes
podinfo/podinfo	6.16.0       	6.16.0     	Podinfo Helm chart for Kubernetes
podinfo/podinfo	6.15.0       	6.15.0     	Podinfo Helm chart for Kubernetes
```

Pour rester sur une série, par exemple les correctifs de la 6.12, donnez une
**contrainte** à `--version`. `~6.12` veut dire « 6.12, avec n'importe quel
correctif » :

```bash
helm search repo podinfo/podinfo --version '~6.12'
```

```text
NAME           	CHART VERSION	APP VERSION	DESCRIPTION
podinfo/podinfo	6.12.0       	6.12.0     	Podinfo Helm chart for Kubernetes
```

La recherche rend la dernière version de cette série, et non la dernière
version tout court.

## 📚 Exercice 2 : ce qu'une nouvelle version change

Avant de monter de version, regardez ce que la nouvelle version change dans
les valeurs par défaut du chart. `helm show values` les affiche, et `diff`
compare les deux sorties :

```bash
diff <(helm show values podinfo/podinfo --version 6.16.0) <(helm show values podinfo/podinfo --version 6.17.0); echo "code $?"
```

```text
11c11
<   tag: 6.16.0
---
>   tag: 6.17.0
98a99,103
>   # call the https backends with SPIFFE mTLS, presenting podinfo's SVID
>   backendMTLS: false
>   # the server SPIFFE IDs accepted from https backends, when empty any ID in podinfo's trust domain is accepted
>   # requires backendMTLS
>   backendIDs: []
code 1
```

Les lignes `<` viennent de la 6.16.0, les lignes `>` de la 6.17.0. Le tag de
l'image change, et la 6.17.0 ajoute deux réglages, `backendMTLS` et
`backendIDs`.

## 📚 Exercice 3 : comparer deux révisions

Créez le namespace d'essai, installez la release `atelier` en version 6.16.0,
puis passez-la à 2 réplicas. `head` et `sed` raccourcissent les sorties :

```bash
kubectl create namespace essai-helm
helm install atelier podinfo/podinfo --version 6.16.0 -n essai-helm --wait --timeout 180s | head -7
helm upgrade atelier podinfo/podinfo --version 6.16.0 -n essai-helm --set replicaCount=2 --wait --timeout 180s | sed -n '4,6p'
```

```text
namespace/essai-helm created
NAME: atelier
LAST DEPLOYED: Fri Nov 20 18:30:38 2026
NAMESPACE: essai-helm
STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete
NOTES:
NAMESPACE: essai-helm
STATUS: deployed
REVISION: 2
```

`helm get manifest --revision` donne les manifestes qu'une révision a envoyés
au cluster. Comparez les révisions 1 et 2 :

```bash
diff <(helm get manifest atelier -n essai-helm --revision 1) <(helm get manifest atelier -n essai-helm --revision 2); echo "code $?"
```

```text
40c40
<   replicas: 1
---
>   replicas: 2
code 1
```

Une seule ligne diffère. Sur une release qui a beaucoup changé, cette
comparaison dit exactement ce qu'une révision a apporté.

## 📚 Exercice 4 : un échec, et Helm revient tout seul

Passez la release en 6.17.0, en demandant par erreur 500 Gio de mémoire pour le
conteneur. `--reuse-values` garde les 2 réplicas, et `--rollback-on-failure`
demande à Helm de revenir en arrière tout seul si la montée échoue :

```bash
helm upgrade atelier podinfo/podinfo --version 6.17.0 -n essai-helm --reuse-values --set resources.requests.memory=500Gi --rollback-on-failure --timeout 45s; echo "code $?"
```

```text
level=WARN msg="upgrade failed" name=atelier error="resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Pending termination: 1\ncontext deadline exceeded"
Error: UPGRADE FAILED: release atelier failed, and has been rolled back due to rollback-on-failure being set: resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Pending termination: 1
context deadline exceeded
code 1
```

La montée a échoué, et Helm l'annonce : `has been rolled back`. Regardez
l'historique et les Pods :

```bash
helm history atelier -n essai-helm | cut -c1-120
kubectl get pods -n essai-helm
```

```text
REVISION	UPDATED                 	STATUS    	CHART         	APP VERSION	DESCRIPTION
1       	Fri Nov 20 18:30:38 2026	superseded	podinfo-6.16.0	6.16.0     	Install complete
2       	Fri Nov 20 18:30:40 2026	superseded	podinfo-6.16.0	6.16.0     	Upgrade complete
3       	Fri Nov 20 18:30:44 2026	failed    	podinfo-6.17.0	6.17.0     	Upgrade "atelier" failed: resource Deployment/es
4       	Fri Nov 20 18:31:29 2026	deployed  	podinfo-6.16.0	6.16.0     	Rollback to 2
NAME                               READY   STATUS    RESTARTS   AGE
atelier-podinfo-848f58c586-vcqvz   1/1     Running   0          53s
atelier-podinfo-848f58c586-zth98   1/1     Running   0          2s
```

La révision 3 a échoué, et Helm a créé la révision 4, `Rollback to 2`. Les
deux Pods tournent de nouveau. Sans cette option, la release resterait en
échec, comme le montre l'exercice suivant.

## 📚 Exercice 5 : deux échecs, puis un retour arrière sans numéro

Refaites la même montée, cette fois sans `--rollback-on-failure`, et regardez
les Pods :

```bash
helm upgrade atelier podinfo/podinfo --version 6.17.0 -n essai-helm --reuse-values --set resources.requests.memory=500Gi --wait --timeout 45s; echo "code $?"
kubectl get pods -n essai-helm
```

```text
level=WARN msg="upgrade failed" name=atelier error="resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Pending termination: 1\ncontext deadline exceeded"
Error: UPGRADE FAILED: resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Pending termination: 1
context deadline exceeded
code 1
NAME                               READY   STATUS    RESTARTS   AGE
atelier-podinfo-848f58c586-vcqvz   1/1     Running   0          98s
atelier-podinfo-86c7bcd589-8v9gz   0/1     Pending   0          45s
atelier-podinfo-86c7bcd589-fqc4x   0/1     Pending   0          45s
```

Les deux nouveaux Pods attendent une place qui n'existe pas (`Pending`), et un
seul ancien Pod sert encore : l'application tourne à moitié. Pourquoi un des
deux anciens Pods a-t-il déjà été arrêté ? La stratégie du Deployment le dit :

```bash
kubectl get deployment atelier-podinfo -n essai-helm -o jsonpath='{.spec.strategy}{"\n"}'
```

```text
{"rollingUpdate":{"maxSurge":"25%","maxUnavailable":1},"type":"RollingUpdate"}
```

`maxUnavailable: 1`, posé par le chart podinfo : pendant une mise à jour, un
Pod peut être indisponible. Kubernetes a arrêté un ancien Pod sans attendre que
les nouveaux soient prêts. Ratez maintenant une seconde montée, avec une autre
valeur fautive, puis relisez l'historique (`cut` coupe les lignes longues) :

```bash
helm upgrade atelier podinfo/podinfo --version 6.17.0 -n essai-helm --reuse-values --set resources.requests.memory=400Gi --wait --timeout 45s 2>&1 | tail -1; helm history atelier -n essai-helm | cut -c1-120
```

```text
context deadline exceeded
REVISION	UPDATED                 	STATUS    	CHART         	APP VERSION	DESCRIPTION
1       	Fri Nov 20 18:30:38 2026	superseded	podinfo-6.16.0	6.16.0     	Install complete
2       	Fri Nov 20 18:30:40 2026	superseded	podinfo-6.16.0	6.16.0     	Upgrade complete
3       	Fri Nov 20 18:30:44 2026	failed    	podinfo-6.17.0	6.17.0     	Upgrade "atelier" failed: resource Deployment/es
4       	Fri Nov 20 18:31:29 2026	deployed  	podinfo-6.16.0	6.16.0     	Rollback to 2
5       	Fri Nov 20 18:31:31 2026	failed    	podinfo-6.17.0	6.17.0     	Upgrade "atelier" failed: resource Deployment/es
6       	Fri Nov 20 18:32:16 2026	failed    	podinfo-6.17.0	6.17.0     	Upgrade "atelier" failed: resource Deployment/es
```

Deux échecs à la suite, les révisions 5 et 6. Lancez un retour arrière **sans
numéro** :

```bash
helm rollback atelier -n essai-helm --wait --timeout 45s; echo "code $?"
helm history atelier -n essai-helm | cut -c1-120 | tail -2
```

```text
Error: release atelier failed: resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Pending termination: 1
context deadline exceeded
code 1
6       	Fri Nov 20 18:32:16 2026	failed    	podinfo-6.17.0	6.17.0     	Upgrade "atelier" failed: resource Deployment/es
7       	Fri Nov 20 18:33:01 2026	failed    	podinfo-6.17.0	6.17.0     	Release "atelier" failed: resource Deployment/es
```

Le retour arrière a échoué lui aussi. Sans numéro, `helm rollback` revient à la
révision **précédente**, quel que soit son statut : ici la 5, elle-même en
échec. La révision 7 est donc une copie d'un échec.

## 📚 Exercice 6 : revenir à la bonne révision, puis tester

La dernière révision saine est la 2, avec 2 réplicas en 6.16.0. Donnez son
numéro :

```bash
helm rollback atelier 2 -n essai-helm --wait --timeout 120s
helm history atelier -n essai-helm | cut -c1-120 | tail -1
kubectl get pods -n essai-helm
```

```text
Rollback was a success! Happy Helming!
8       	Fri Nov 20 18:33:47 2026	deployed  	podinfo-6.16.0	6.16.0     	Rollback to 2
NAME                               READY   STATUS    RESTARTS   AGE
atelier-podinfo-848f58c586-vcqvz   1/1     Running   0          3m11s
atelier-podinfo-848f58c586-zjsnm   1/1     Running   0          2s
```

La révision 8 est déployée, et les deux Pods tournent. Lancez les tests du
chart sur cette révision. `sed` ne garde que la révision et le résultat de
chaque test :

```bash
helm test atelier -n essai-helm | sed -n '/^REVISION/p;/^DESCRIPTION/p;/Phase/p'
```

```text
REVISION: 8
DESCRIPTION: Rollback to 2
Phase:          Succeeded
Phase:          Succeeded
Phase:          Succeeded
```

Trois tests réussis, sur la révision 8.

## 🧹 Nettoyage

Désinstallez la release d'essai, puis supprimez son namespace :

```bash
helm uninstall atelier -n essai-helm --wait; kubectl delete namespace essai-helm
```

```text
release "atelier" uninstalled
namespace "essai-helm" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-inspecter-et-restaurer-une-release-helm
dsoxlab check k8s-inspecter-et-restaurer-une-release-helm
```

```text
╭─ Résultat : k8s-inspecter-et-restaurer-une-release-helm ─╮
│  0 / 100 pts                                             │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                         │
╰──────────────────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une autre release, déjà en échec dans un autre
namespace. Relevez la dernière version d'une série du chart et les révisions
fautives, revenez à la dernière révision saine, puis lancez les tests.

```bash
dsoxlab run k8s-inspecter-et-restaurer-une-release-helm
dsoxlab challenge k8s-inspecter-et-restaurer-une-release-helm
```
