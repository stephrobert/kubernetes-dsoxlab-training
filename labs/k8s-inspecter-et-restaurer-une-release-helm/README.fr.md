# Inspecter une release Helm en échec et la restaurer

**Helm** installe une application à partir d'un **chart**, un paquet de
manifestes paramétrables. Chaque installation s'appelle une **release**, et
chaque modification de la release crée une nouvelle **révision**. Dans ce
cours, vous cherchez un chart dans un dépôt, vous installez une release, vous
la décrivez, vous ratez une montée de version, vous trouvez pourquoi, vous
revenez en arrière, puis vous lancez les tests du chart.

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
19 novembre 2026, avec Kubernetes v1.37.2 et Helm 4.3.2.

## 📚 Exercice 1 : chercher un chart

Vérifiez la version de Helm et les dépôts de charts déclarés :

```bash
helm version --short; helm repo list
```

```text
v4.3.2+g8346aaa
NAME   	URL                                   
podinfo	https://stefanprodan.github.io/podinfo
```

Le lab a déclaré le dépôt `podinfo`. `helm search repo` cherche un chart dans
les dépôts déclarés, et affiche sa dernière version :

```bash
helm search repo podinfo/podinfo
```

```text
NAME           	CHART VERSION	APP VERSION	DESCRIPTION                      
podinfo/podinfo	6.17.0       	6.17.0     	Podinfo Helm chart for Kubernetes
```

`CHART VERSION` est la version du chart, `APP VERSION` celle de l'application
qu'il installe. `--versions` liste toutes les versions publiées, de la plus
récente à la plus ancienne :

```bash
helm search repo podinfo/podinfo --versions | head -5
```

```text
NAME           	CHART VERSION	APP VERSION	DESCRIPTION                      
podinfo/podinfo	6.17.0       	6.17.0     	Podinfo Helm chart for Kubernetes
podinfo/podinfo	6.16.0       	6.16.0     	Podinfo Helm chart for Kubernetes
podinfo/podinfo	6.15.0       	6.15.0     	Podinfo Helm chart for Kubernetes
podinfo/podinfo	6.14.1       	6.14.1     	Podinfo Helm chart for Kubernetes
```

## 📚 Exercice 2 : installer une release

Créez le namespace d'essai, puis installez la release `atelier` avec la
version 6.16.0 du chart. `--wait` attend que l'application soit prête, et
`head` raccourcit la sortie :

```bash
kubectl create namespace essai-helm
helm install atelier podinfo/podinfo --version 6.16.0 -n essai-helm --wait --timeout 180s | head -7
```

```text
namespace/essai-helm created
NAME: atelier
LAST DEPLOYED: Thu Nov 19 19:45:23 2026
NAMESPACE: essai-helm
STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete
NOTES:
```

`helm list` affiche les releases d'un namespace :

```bash
helm list -n essai-helm
```

```text
NAME   	NAMESPACE 	REVISION	UPDATED                                	STATUS  	CHART         	APP VERSION
atelier	essai-helm	1       	2026-11-19 19:45:23.128326202 +0000 UTC	deployed	podinfo-6.16.0	6.16.0     
```

Révision 1, statut `deployed` : la release est installée et fonctionne.

## 📚 Exercice 3 : décrire une release

`helm status` donne l'état de la release :

```bash
helm status atelier -n essai-helm | head -7
```

```text
NAME: atelier
LAST DEPLOYED: Thu Nov 19 19:45:23 2026
NAMESPACE: essai-helm
STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete
RESOURCES:
```

`helm get` lit ce que la release contient. `helm get values` montre les
valeurs que vous avez passées au chart :

```bash
helm get values atelier -n essai-helm
```

```text
USER-SUPPLIED VALUES:
null
```

`null` : aucune, le chart utilise ses valeurs par défaut. `helm get manifest`
montre les manifestes que Helm a envoyés au cluster. `grep` ne garde que leur
type :

```bash
helm get manifest atelier -n essai-helm | grep -E '^kind:'
```

```text
kind: Service
kind: Deployment
```

## 📚 Exercice 4 : une montée de version qui échoue

Passez la release à la version 6.17.0 du chart, en demandant par erreur
500 Gio de mémoire pour le conteneur (`--set` change une valeur du chart) :

```bash
helm upgrade atelier podinfo/podinfo --version 6.17.0 -n essai-helm --set resources.requests.memory=500Gi --wait --timeout 45s
```

```text
level=WARN msg="upgrade failed" name=atelier error="resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Available: 0/1\ncontext deadline exceeded"
Error: UPGRADE FAILED: resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Available: 0/1
context deadline exceeded
```

Au bout des 45 secondes, le Deployment n'est toujours pas prêt : Helm déclare
l'échec. `helm history` liste toutes les révisions, avec leur statut :

```bash
helm history atelier -n essai-helm
```

```text
REVISION	UPDATED                 	STATUS  	CHART         	APP VERSION	DESCRIPTION                                                                                                                    
1       	Thu Nov 19 19:45:23 2026	deployed	podinfo-6.16.0	6.16.0     	Install complete                                                                                                               
2       	Thu Nov 19 19:45:26 2026	failed  	podinfo-6.17.0	6.17.0     	Upgrade "atelier" failed: resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Available: ...
```

La révision 2 est en échec (`failed`). `helm status` décrit maintenant cette
révision :

```bash
helm status atelier -n essai-helm | head -7
```

```text
NAME: atelier
LAST DEPLOYED: Thu Nov 19 19:45:26 2026
NAMESPACE: essai-helm
STATUS: failed
REVISION: 2
DESCRIPTION: Upgrade "atelier" failed: resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Available: 0/1
context deadline exceeded
```

## 📚 Exercice 5 : comprendre l'échec

`--revision` lit une révision précise. Voici les valeurs de la révision 2 :

```bash
helm get values atelier -n essai-helm --revision 2
```

```text
USER-SUPPLIED VALUES:
resources:
  requests:
    memory: 500Gi
```

C'est le changement fautif. Regardez les Pods :

```bash
kubectl get pods -n essai-helm
```

```text
NAME                               READY   STATUS    RESTARTS   AGE
atelier-podinfo-74575b5dfb-7bg97   0/1     Pending   0          45s
```

Un seul Pod, en attente (`Pending`). L'ancien Pod a déjà été arrêté :
l'application ne répond plus du tout. Les événements disent pourquoi le nouveau
Pod ne trouve pas de place :

```bash
kubectl get events -n essai-helm --field-selector reason=FailedScheduling -o custom-columns=MESSAGE:.message | tail -1
```

```text
0/2 nodes are available: 2 Insufficient memory. preemption: 0/2 nodes are available: 2 Preemption is not helpful for scheduling.
```

Aucun des deux nœuds n'a 500 Gio de mémoire.

## 📚 Exercice 6 : revenir en arrière

La dernière révision saine est la 1. `helm rollback` y revient :

```bash
helm rollback atelier 1 -n essai-helm --wait --timeout 120s
```

```text
Rollback was a success! Happy Helming!
```

Relisez l'historique :

```bash
helm history atelier -n essai-helm
```

```text
REVISION	UPDATED                 	STATUS    	CHART         	APP VERSION	DESCRIPTION                                                                                                                    
1       	Thu Nov 19 19:45:23 2026	superseded	podinfo-6.16.0	6.16.0     	Install complete                                                                                                               
2       	Thu Nov 19 19:45:26 2026	failed    	podinfo-6.17.0	6.17.0     	Upgrade "atelier" failed: resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Available: ...
3       	Thu Nov 19 19:46:11 2026	deployed  	podinfo-6.16.0	6.16.0     	Rollback to 1                                                                                                                  
```

Le retour arrière n'a rien effacé. Il a créé une **révision 3**, copie de la
révision 1 (`Rollback to 1`). La révision 1 est maintenant `superseded`
(remplacée), et la révision 2 garde la trace de l'échec. L'application tourne
de nouveau :

```bash
kubectl get pods -n essai-helm
```

```text
NAME                               READY   STATUS    RESTARTS   AGE
atelier-podinfo-848f58c586-25wg9   1/1     Running   0          3s
```

## 📚 Exercice 7 : lancer les tests du chart

Un chart peut embarquer des tests : des Pods qui vérifient que l'application
répond. `helm test` les lance sur la révision courante :

```bash
helm test atelier -n essai-helm
```

```text
NAME: atelier
LAST DEPLOYED: Thu Nov 19 19:46:11 2026
NAMESPACE: essai-helm
STATUS: deployed
REVISION: 3
DESCRIPTION: Rollback to 1
TEST SUITE:     atelier-podinfo-grpc-test-9y20y
Last Started:   Thu Nov 19 19:46:14 2026
Last Completed: Thu Nov 19 19:46:19 2026
Phase:          Succeeded
TEST SUITE:     atelier-podinfo-jwt-test-hltiu
Last Started:   Thu Nov 19 19:46:19 2026
Last Completed: Thu Nov 19 19:46:24 2026
Phase:          Succeeded
TEST SUITE:     atelier-podinfo-service-test-y13sp
Last Started:   Thu Nov 19 19:46:24 2026
Last Completed: Thu Nov 19 19:46:29 2026
Phase:          Succeeded
```

Trois tests, tous réussis (`Succeeded`), sur la révision 3. Leur résultat
reste attaché à la release : `helm status` le montre encore ensuite.
`sed` affiche la sortie à partir du premier `TEST SUITE` :

```bash
helm status atelier -n essai-helm | sed -n '/TEST SUITE/,/^$/p'
```

```text
TEST SUITE:     atelier-podinfo-grpc-test-9y20y
Last Started:   Thu Nov 19 19:46:14 2026
Last Completed: Thu Nov 19 19:46:19 2026
Phase:          Succeeded
TEST SUITE:     atelier-podinfo-jwt-test-hltiu
Last Started:   Thu Nov 19 19:46:19 2026
Last Completed: Thu Nov 19 19:46:24 2026
Phase:          Succeeded
TEST SUITE:     atelier-podinfo-service-test-y13sp
Last Started:   Thu Nov 19 19:46:24 2026
Last Completed: Thu Nov 19 19:46:29 2026
Phase:          Succeeded
NOTES:
1. Get the application URL by running these commands:
  echo "Visit http://127.0.0.1:8080 to use your application"
  kubectl -n essai-helm port-forward deploy/atelier-podinfo 8080:9898
```

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
namespace. Relevez la dernière version du chart et la révision fautive,
revenez à la dernière révision saine, puis lancez les tests.

```bash
dsoxlab run k8s-inspecter-et-restaurer-une-release-helm
dsoxlab challenge k8s-inspecter-et-restaurer-une-release-helm
```
