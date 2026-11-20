# Installer, mettre à jour et revenir en arrière avec Helm 4

Un **chart** Helm est un répertoire : des modèles de manifestes, et un fichier
de **valeurs** qui les remplit. Dans ce cours, vous créez un chart, vous le
vérifiez, vous l'installez et vous changez ses valeurs. Vous revenez ensuite
en arrière de trois façons : vers une révision précise, sans numéro, et après
une désinstallation. Vous verrez aussi `upgrade --install`, qui installe ou
met à jour selon que la release existe ou non.

Vous travaillez avec un chart d'essai, `bonjour`, dans un namespace d'essai,
`essai-chart`. Le challenge porte sur un autre chart, déjà préparé : vous le
ferez seul, à la fin.

Page associée : [Installer et gérer des releases Helm](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/helm/install-releases/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-helm-install-upgrade
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà, et le lab a installé
Helm.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026, avec Kubernetes v1.37.2 et Helm 4.3.2.

## 📚 Exercice 1 : créer un chart

`helm create` crée un chart d'exemple complet. Créez-le dans un répertoire de
travail :

```bash
mkdir -p ~/essai-charts && cd ~/essai-charts && helm create bonjour
```

```text
Creating bonjour
```

Voici ses fichiers :

```bash
cd ~/essai-charts && find bonjour -type f | sort
```

```text
bonjour/.helmignore
bonjour/Chart.yaml
bonjour/templates/NOTES.txt
bonjour/templates/_helpers.tpl
bonjour/templates/deployment.yaml
bonjour/templates/hpa.yaml
bonjour/templates/httproute.yaml
bonjour/templates/ingress.yaml
bonjour/templates/service.yaml
bonjour/templates/serviceaccount.yaml
bonjour/templates/tests/test-connection.yaml
bonjour/values.yaml
```

Trois choses comptent :

- `Chart.yaml` décrit le chart (son nom, sa version) ;
- `values.yaml` porte les valeurs par défaut ;
- `templates/` contient les modèles de manifestes, que Helm remplit avec les
  valeurs.

## 📚 Exercice 2 : les valeurs d'un chart

Lisez l'identité du chart :

```bash
grep -E '^(name|version|appVersion):' ~/essai-charts/bonjour/Chart.yaml
```

```text
name: bonjour
version: 0.1.0
appVersion: "1.16.0"
```

`version` est la version du chart. `appVersion` est celle de l'application
qu'il est censé installer. Lisez maintenant quelques valeurs par défaut :

```bash
grep -n -E '^replicaCount|^image:|^  repository:|^  tag:' ~/essai-charts/bonjour/values.yaml
```

```text
6:replicaCount: 1
9:image:
10:  repository: nginx
14:  tag: ""
```

1 réplica, image `nginx`, tag vide. Le modèle du Deployment montre comment ces
valeurs sont utilisées :

```bash
grep -n 'image:' ~/essai-charts/bonjour/templates/deployment.yaml
```

```text
41:          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
```

Les `{{ }}` sont remplacés par Helm. Si `image.tag` est vide, Helm prend
`appVersion` à la place : l'image serait `nginx:1.16.0`, une version très
ancienne. Donnez au tag une version récente, avec son digest :

```bash
sed -i 's|^  tag: ""|  tag: "1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"|' ~/essai-charts/bonjour/values.yaml; grep -n '^  tag:' ~/essai-charts/bonjour/values.yaml
```

```text
14:  tag: "1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
```

## 📚 Exercice 3 : vérifier avant d'installer

`helm lint` cherche les erreurs dans un chart :

```bash
helm lint ~/essai-charts/bonjour
```

```text
==> Linting /home/ansible/essai-charts/bonjour
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

Aucune erreur, juste une suggestion (ajouter une icône). `helm template`
affiche les manifestes produits, sans rien installer. `grep` ne garde que leur
type, le nombre de réplicas et les images :

```bash
helm template bonjour ~/essai-charts/bonjour | grep -E '^kind:|replicas:|image:'
```

```text
kind: ServiceAccount
kind: Service
kind: Deployment
  replicas: 1
          image: "nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
kind: Pod
      image: busybox
```

Le Deployment utilise bien votre tag. Le `Pod` à la fin est le test du chart
(`templates/tests/`) : il ne sera lancé que par `helm test`.

## 📚 Exercice 4 : installer depuis un répertoire

Créez le namespace d'essai, puis installez le chart depuis son répertoire,
sous le nom de release `bonjour` :

```bash
kubectl create namespace essai-chart
helm install bonjour ~/essai-charts/bonjour -n essai-chart --wait --timeout 180s | head -6
kubectl get deployment -n essai-chart
```

```text
namespace/essai-chart created
NAME: bonjour
LAST DEPLOYED: Fri Nov 20 19:02:52 2026
NAMESPACE: essai-chart
STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
bonjour   1/1     1            1           1s
```

Révision 1, avec 1 réplica, la valeur par défaut.

## 📚 Exercice 5 : changer une valeur

`--set` change une valeur à la ligne de commande, sans toucher au fichier.
Passez à 3 réplicas :

```bash
helm upgrade bonjour ~/essai-charts/bonjour -n essai-chart --set replicaCount=3 --wait --timeout 180s | head -6
```

```text
Release "bonjour" has been upgraded. Happy Helming!
NAME: bonjour
LAST DEPLOYED: Fri Nov 20 19:02:53 2026
NAMESPACE: essai-chart
STATUS: deployed
REVISION: 2
```

`helm get values` montre les valeurs que vous avez passées :

```bash
helm get values bonjour -n essai-chart; kubectl get deployment -n essai-chart
```

```text
USER-SUPPLIED VALUES:
replicaCount: 3
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
bonjour   3/3     3            3           12s
```

## 📚 Exercice 6 : un upgrade avec une autre valeur

Que deviennent les valeurs passées au tour précédent ? Relancez d'abord un
`upgrade` **sans aucune valeur** :

```bash
helm upgrade bonjour ~/essai-charts/bonjour -n essai-chart --wait --timeout 180s > /dev/null; helm get values bonjour -n essai-chart; kubectl get deployment -n essai-chart
```

```text
USER-SUPPLIED VALUES:
replicaCount: 3
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
bonjour   3/3     3            3           13s
```

Sans aucune valeur, Helm reprend celles de la révision précédente : toujours
3 réplicas. Passez maintenant **une autre** valeur, un label `equipe` sur les
Pods :

```bash
helm upgrade bonjour ~/essai-charts/bonjour -n essai-chart --set podLabels.equipe=accueil --wait --timeout 180s > /dev/null; helm get values bonjour -n essai-chart; kubectl get deployment -n essai-chart
```

```text
USER-SUPPLIED VALUES:
podLabels:
  equipe: accueil
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
bonjour   1/1     1            1           15s
```

Retour à 1 réplica. Dès que vous passez une valeur, Helm repart des valeurs par
défaut du chart, plus **seulement** celles de cette commande : `replicaCount=3`
est perdu. `--reuse-values` garde les valeurs précédentes et y ajoute les
nouvelles :

```bash
helm upgrade bonjour ~/essai-charts/bonjour -n essai-chart --reuse-values --set replicaCount=3 --wait --timeout 180s > /dev/null; helm get values bonjour -n essai-chart; kubectl get deployment -n essai-chart
```

```text
USER-SUPPLIED VALUES:
podLabels:
  equipe: accueil
replicaCount: 3
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
bonjour   3/3     3            3           16s
```

Les deux valeurs sont là. Chaque `upgrade` a créé une révision :

```bash
helm history bonjour -n essai-chart
```

```text
REVISION	UPDATED                 	STATUS    	CHART        	APP VERSION	DESCRIPTION     
1       	Fri Nov 20 19:02:52 2026	superseded	bonjour-0.1.0	1.16.0     	Install complete
2       	Fri Nov 20 19:02:53 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
3       	Fri Nov 20 19:03:04 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
4       	Fri Nov 20 19:03:05 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
5       	Fri Nov 20 19:03:07 2026	deployed  	bonjour-0.1.0	1.16.0     	Upgrade complete
```

La colonne `CHART` donne le nom et la version du chart utilisés par chaque
révision : ici toujours `bonjour-0.1.0`, puisque `Chart.yaml` n'a pas changé.
La colonne `APP VERSION` affiche `1.16.0`, l'`appVersion` du chart, alors que
l'image tourne en 1.30.5 : cette colonne recopie `Chart.yaml`, elle ne lit pas
l'image.

## 📚 Exercice 7 : revenir à une révision

Revenez à la révision 2, celle avec 3 réplicas et sans label :

```bash
helm rollback bonjour 2 -n essai-chart --wait --timeout 180s
```

```text
Rollback was a success! Happy Helming!
```

```bash
helm history bonjour -n essai-chart; helm get values bonjour -n essai-chart; kubectl get deployment -n essai-chart
```

```text
REVISION	UPDATED                 	STATUS    	CHART        	APP VERSION	DESCRIPTION     
1       	Fri Nov 20 19:02:52 2026	superseded	bonjour-0.1.0	1.16.0     	Install complete
2       	Fri Nov 20 19:02:53 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
3       	Fri Nov 20 19:03:04 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
4       	Fri Nov 20 19:03:05 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
5       	Fri Nov 20 19:03:07 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
6       	Fri Nov 20 19:03:09 2026	deployed  	bonjour-0.1.0	1.16.0     	Rollback to 2   
USER-SUPPLIED VALUES:
replicaCount: 3
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
bonjour   3/3     3            3           20s
```

Une révision 6 est née (`Rollback to 2`), avec les valeurs de la révision 2 :
3 réplicas, plus de label. Vérifiez que l'application répond, sur l'adresse
interne de son Service (`grep -o` ne garde que le titre de la page) :

```bash
IP=$(kubectl get service bonjour -n essai-chart -o jsonpath='{.spec.clusterIP}'); curl -s "http://$IP" | grep -o '<title>.*</title>'
```

```text
<title>Welcome to nginx!</title>
```

## 📚 Exercice 8 : un rollback sans numéro

Faites une montée de plus, à 2 réplicas :

```bash
helm upgrade bonjour ~/essai-charts/bonjour -n essai-chart --reuse-values --set replicaCount=2 --wait --timeout 180s > /dev/null; helm history bonjour -n essai-chart
```

```text
REVISION	UPDATED                 	STATUS    	CHART        	APP VERSION	DESCRIPTION     
1       	Fri Nov 20 19:02:52 2026	superseded	bonjour-0.1.0	1.16.0     	Install complete
2       	Fri Nov 20 19:02:53 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
3       	Fri Nov 20 19:03:04 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
4       	Fri Nov 20 19:03:05 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
5       	Fri Nov 20 19:03:07 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
6       	Fri Nov 20 19:03:09 2026	superseded	bonjour-0.1.0	1.16.0     	Rollback to 2   
7       	Fri Nov 20 19:03:12 2026	deployed  	bonjour-0.1.0	1.16.0     	Upgrade complete
```

Sans numéro, `helm rollback` revient à la révision qui précède la révision
courante :

```bash
helm rollback bonjour -n essai-chart --wait --timeout 180s
```

```text
Rollback was a success! Happy Helming!
```

```bash
helm history bonjour -n essai-chart; helm get values bonjour -n essai-chart
```

```text
REVISION	UPDATED                 	STATUS    	CHART        	APP VERSION	DESCRIPTION     
1       	Fri Nov 20 19:02:52 2026	superseded	bonjour-0.1.0	1.16.0     	Install complete
2       	Fri Nov 20 19:02:53 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
3       	Fri Nov 20 19:03:04 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
4       	Fri Nov 20 19:03:05 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
5       	Fri Nov 20 19:03:07 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
6       	Fri Nov 20 19:03:09 2026	superseded	bonjour-0.1.0	1.16.0     	Rollback to 2   
7       	Fri Nov 20 19:03:12 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
8       	Fri Nov 20 19:03:12 2026	deployed  	bonjour-0.1.0	1.16.0     	Rollback to 6   
USER-SUPPLIED VALUES:
replicaCount: 3
```

La révision 8 dit `Rollback to 6` : la révision précédente était le rollback
de l'exercice 7, et non la révision 1 ni la 2. Sans numéro, Helm ne remonte
que d'un cran, quel que soit le contenu de ce cran. Pour viser une révision
précise, donnez son numéro.

## 📚 Exercice 9 : upgrade --install, deux fois

`helm install` échoue si la release existe déjà (`cannot reuse a name that is
still in use`), et `helm upgrade` échoue si elle n'existe pas (`has no
deployed releases`). `helm upgrade --install` fait l'un ou l'autre : c'est la
commande qu'on rejoue sans se poser de question, dans un script ou une
pipeline. Regardez d'abord les releases du namespace :

```bash
helm list -n essai-chart
```

```text
NAME   	NAMESPACE  	REVISION	UPDATED                                	STATUS  	CHART        	APP VERSION
bonjour	essai-chart	8       	2026-11-20 19:03:12.748038061 +0000 UTC	deployed	bonjour-0.1.0	1.16.0     
```

Lancez `upgrade --install` pour une release `salut` qui n'existe pas :

```bash
helm upgrade --install salut ~/essai-charts/bonjour -n essai-chart --wait --timeout 180s | head -6
```

```text
Release "salut" does not exist. Installing it now.
NAME: salut
LAST DEPLOYED: Fri Nov 20 19:03:14 2026
NAMESPACE: essai-chart
STATUS: deployed
REVISION: 1
```

Helm l'a installée. Relancez exactement la même commande :

```bash
helm upgrade --install salut ~/essai-charts/bonjour -n essai-chart --wait --timeout 180s | head -6
```

```text
Release "salut" has been upgraded. Happy Helming!
NAME: salut
LAST DEPLOYED: Fri Nov 20 19:03:15 2026
NAMESPACE: essai-chart
STATUS: deployed
REVISION: 2
```

Cette fois, c'est une mise à jour. L'historique montre les deux :

```bash
helm history salut -n essai-chart
```

```text
REVISION	UPDATED                 	STATUS    	CHART        	APP VERSION	DESCRIPTION     
1       	Fri Nov 20 19:03:14 2026	superseded	bonjour-0.1.0	1.16.0     	Install complete
2       	Fri Nov 20 19:03:15 2026	deployed  	bonjour-0.1.0	1.16.0     	Upgrade complete
```

## 📚 Exercice 10 : désinstaller en gardant l'historique

`helm uninstall` supprime les objets de la release et, par défaut, son
historique. Avec `--keep-history`, l'historique reste :

```bash
helm uninstall salut -n essai-chart --keep-history --wait
```

```text
release "salut" uninstalled
```

```bash
helm list -n essai-chart; helm list -n essai-chart --uninstalled
```

```text
NAME   	NAMESPACE  	REVISION	UPDATED                                	STATUS     	CHART        	APP VERSION
bonjour	essai-chart	8       	2026-11-20 19:03:12.748038061 +0000 UTC	deployed   	bonjour-0.1.0	1.16.0     
salut  	essai-chart	2       	2026-11-20 19:03:15.885798202 +0000 UTC	uninstalled	bonjour-0.1.0	1.16.0     
NAME 	NAMESPACE  	REVISION	UPDATED                                	STATUS     	CHART        	APP VERSION
salut	essai-chart	2       	2026-11-20 19:03:15.885798202 +0000 UTC	uninstalled	bonjour-0.1.0	1.16.0     
```

Avec Helm 4.3.2, `helm list` sans option montre aussi la release
désinstallée, avec le statut `uninstalled`. `--uninstalled` ne garde que
celles-là. Les objets, eux, ont disparu :

```bash
helm history salut -n essai-chart; kubectl get deployment -n essai-chart
```

```text
REVISION	UPDATED                 	STATUS     	CHART        	APP VERSION	DESCRIPTION            
1       	Fri Nov 20 19:03:14 2026	superseded 	bonjour-0.1.0	1.16.0     	Install complete       
2       	Fri Nov 20 19:03:15 2026	uninstalled	bonjour-0.1.0	1.16.0     	Uninstallation complete
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
bonjour   3/3     3            3           24s
```

Plus de Deployment `salut-bonjour`. Le nom reste pris tant que l'historique
existe, même pour un `helm install` :

```bash
helm install salut ~/essai-charts/bonjour -n essai-chart 2>&1 | tail -1
```

```text
Error: INSTALLATION FAILED: release name check failed: cannot reuse a name that is still in use
```

Un rollback, lui, fonctionne : il recrée les objets à partir d'une révision
conservée.

```bash
helm rollback salut 1 -n essai-chart --wait --timeout 180s
```

```text
Rollback was a success! Happy Helming!
```

```bash
helm history salut -n essai-chart; kubectl get deployment -n essai-chart
```

```text
REVISION	UPDATED                 	STATUS     	CHART        	APP VERSION	DESCRIPTION            
1       	Fri Nov 20 19:03:14 2026	superseded 	bonjour-0.1.0	1.16.0     	Install complete       
2       	Fri Nov 20 19:03:15 2026	uninstalled	bonjour-0.1.0	1.16.0     	Uninstallation complete
3       	Fri Nov 20 19:03:16 2026	deployed   	bonjour-0.1.0	1.16.0     	Rollback to 1          
NAME            READY   UP-TO-DATE   AVAILABLE   AGE
bonjour         3/3     3            3           25s
salut-bonjour   1/1     1            1           1s
```

La révision 3 reprend la révision 1, et `salut-bonjour` est revenu. Sans
`--keep-history`, il n'y aurait plus rien à reprendre.

## 🧹 Nettoyage

Désinstallez les deux releases, supprimez le namespace et le chart d'essai :

```bash
helm uninstall bonjour salut -n essai-chart --wait; kubectl delete namespace essai-chart; rm -rf ~/essai-charts
```

```text
release "bonjour" uninstalled
release "salut" uninstalled
namespace "essai-chart" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-helm-install-upgrade
dsoxlab check ckad-helm-install-upgrade
```

```text
╭─ Résultat : ckad-helm-install-upgrade ─╮
│  0 / 100 pts                           │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests       │
╰────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un autre chart, déjà préparé. Installez-le, faites
monter sa version, mettez la release à jour avec de nouvelles valeurs, puis
revenez à sa première révision.

```bash
dsoxlab run ckad-helm-install-upgrade
dsoxlab challenge ckad-helm-install-upgrade
```
