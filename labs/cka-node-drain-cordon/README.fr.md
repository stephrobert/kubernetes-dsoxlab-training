# Vider un worker pour une maintenance, sans couper le service

La leçon montre comment préparer une maintenance : `cordon`, `drain`, et un
PodDisruptionBudget qui protège l'application. Ce cours regarde ce qui se
passe sous `drain` et ajoute des cas que la leçon ne montre pas : une
éviction demandée à la main à l'API, le refus d'un budget déjà consommé, et
un drain joué à blanc côté serveur, qui attend que le budget le laisse
passer.

Vous travaillez dans un namespace d'essai, `essai-maintenance`, avec un
Deployment `comptoir` et son budget `comptoir-pdb`. Aucun nœud n'est vidé
pour de vrai. Le challenge porte sur d'autres objets : vous le ferez seul, à
la fin.

Page associée : [Préparer une maintenance de cluster Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/preparer-maintenance-cluster-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-node-drain-cordon
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Créez le namespace, un Deployment de trois réplicas et un budget qui tolère
un seul Pod indisponible à la fois. La sonde de disponibilité attend 20
secondes : un Pod remplacé met donc du temps à redevenir prêt, ce qui laisse
le temps d'observer le budget.

```bash
kubectl create namespace essai-maintenance; kubectl create deployment comptoir --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb --replicas=3 -n essai-maintenance >/dev/null; kubectl patch deployment comptoir -n essai-maintenance --type=json -p '[{"op":"add","path":"/spec/template/spec/containers/0/readinessProbe","value":{"httpGet":{"port":80},"initialDelaySeconds":20}}]' >/dev/null; kubectl rollout status deployment/comptoir -n essai-maintenance --timeout=120s >/dev/null; kubectl create poddisruptionbudget comptoir-pdb -n essai-maintenance --selector=app=comptoir --max-unavailable=1; sleep 3; kubectl get pdb comptoir-pdb -n essai-maintenance
```

```text
namespace/essai-maintenance created
poddisruptionbudget.policy/comptoir-pdb created
NAME           MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
comptoir-pdb   N/A             1                 1                     3s
```

`ALLOWED DISRUPTIONS` vaut 1 : le budget accepte une interruption.

## 📨 Exercice 1 : demander une éviction à la main

`kubectl drain` ne supprime pas les Pods : il demande leur éviction à l'API,
Pod par Pod, en envoyant un objet `Eviction`. Faites-le vous-même pour un Pod
de `comptoir`, puis relisez le budget :

```bash
P=$(kubectl get pods -n essai-maintenance -l app=comptoir -o jsonpath='{.items[0].metadata.name}'); printf '{"apiVersion":"policy/v1","kind":"Eviction","metadata":{"name":"%s","namespace":"essai-maintenance"}}' $P | kubectl create --raw /api/v1/namespaces/essai-maintenance/pods/$P/eviction -f - 2>&1 | cut -c1-200; echo; kubectl get pdb comptoir-pdb -n essai-maintenance
```

```text
{"kind":"Status","apiVersion":"v1","metadata":{},"status":"Success","code":201}

NAME           MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
comptoir-pdb   N/A             1                 0                     3s
```

L'API a accepté (code 201) et le Pod est parti. Le Deployment en crée un
autre, mais il n'est pas encore prêt : le budget n'autorise plus aucune
interruption.

## 🚫 Exercice 2 : le budget refuse la suivante

Demandez tout de suite l'éviction d'un deuxième Pod :

```bash
P=$(kubectl get pods -n essai-maintenance -l app=comptoir --field-selector status.phase=Running -o jsonpath='{.items[1].metadata.name}'); printf '{"apiVersion":"policy/v1","kind":"Eviction","metadata":{"name":"%s","namespace":"essai-maintenance"}}' $P | kubectl create --raw /api/v1/namespaces/essai-maintenance/pods/$P/eviction -f - 2>&1 | cut -c1-200
```

```text
Error from server (TooManyRequests): Cannot evict pod as it would violate the pod's disruption budget.
```

Refusé avec le code HTTP 429 (`TooManyRequests`) : évincer ce Pod laisserait
deux Pods indisponibles. Rien n'a été supprimé. Attendez que le remplaçant
soit prêt, puis recommencez :

```bash
kubectl rollout status deployment/comptoir -n essai-maintenance --timeout=120s >/dev/null; sleep 3; kubectl get pdb comptoir-pdb -n essai-maintenance; P=$(kubectl get pods -n essai-maintenance -l app=comptoir -o jsonpath='{.items[0].metadata.name}'); printf '{"apiVersion":"policy/v1","kind":"Eviction","metadata":{"name":"%s","namespace":"essai-maintenance"}}' $P | kubectl create --raw /api/v1/namespaces/essai-maintenance/pods/$P/eviction -f - 2>&1 | cut -c1-200
```

```text
NAME           MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
comptoir-pdb   N/A             1                 1                     28s
{"kind":"Status","apiVersion":"v1","metadata":{},"status":"Success","code":201}
```

Le budget autorise de nouveau une interruption, et l'éviction passe. C'est
exactement ce que fait `drain` sur un nœud : il réessaie tant que le budget
refuse.

## 🧪 Exercice 3 : un drain à blanc, joué par le serveur

`--dry-run=server` envoie les vraies demandes d'éviction à l'API, qui les
contrôle sans rien exécuter. Contrairement à `--dry-run=client`, les budgets
sont donc vraiment consultés. Simulez le drain du control plane, juste après
l'exercice 2, pendant que le dernier remplaçant n'est pas encore prêt :

```bash
kubectl drain k8s-cp.lab --dry-run=server --ignore-daemonsets --delete-emptydir-data 2>&1 | tail -6 | cut -c1-160
```

```text
evicting pod essai-maintenance/comptoir-5478b99cd8-sz2jr (server dry run)
error when evicting pods/"comptoir-5478b99cd8-sz2jr" -n "essai-maintenance" (will retry after 5s): Cannot evict pod as it would violate the pod's disruption bud
evicting pod essai-maintenance/comptoir-5478b99cd8-sz2jr (server dry run)
error when evicting pods/"comptoir-5478b99cd8-sz2jr" -n "essai-maintenance" (will retry after 5s): Cannot evict pod as it would violate the pod's disruption bud
evicting pod essai-maintenance/comptoir-5478b99cd8-sz2jr (server dry run)
node/k8s-cp.lab drained (server dry run)
```

Un Pod de `comptoir` tournait ici sur le control plane. Le budget refuse
d'abord son éviction, et `drain` réessaie toutes les 5 secondes, jusqu'à ce
que le remplaçant soit prêt. Si vous lancez la commande plus de 20 secondes
après l'exercice 2, ou si aucun Pod de `comptoir` ne tourne sur ce nœud, vous
ne verrez pas de refus. Sur un vrai drain, ce sont ces lignes qui expliquent
un drain qui ne finit pas. Vérifiez que le nœud n'a pas été touché :

```bash
kubectl get node k8s-cp.lab -o jsonpath='ordonnançable={.spec.unschedulable}{"\n"}'
```

```text
ordonnançable=
```

Champ vide : le nœud accepte toujours des Pods. Le drain à blanc n'a pas non
plus appliqué `cordon`.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-maintenance
```

```text
namespace "essai-maintenance" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-node-drain-cordon
dsoxlab check cka-node-drain-cordon
```

```text
╭─ Résultat : cka-node-drain-cordon ─╮
│  0 / 100 pts                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests   │
╰────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un worker à vider pour une maintenance sans couper
le service, puis à remettre en service.

```bash
dsoxlab run cka-node-drain-cordon
dsoxlab challenge cka-node-drain-cordon
```
