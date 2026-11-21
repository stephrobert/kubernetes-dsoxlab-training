# Prioriser des Pods et observer une préemption

La leçon montre les PriorityClass : une valeur de priorité donnée aux Pods,
et la préemption, quand le scheduler retire des Pods moins prioritaires pour
faire de la place à un Pod plus prioritaire. Ce cours ajoute des cas que la
leçon ne montre pas : une classe qui n'existe pas, une priorité écrite à la
main, la valeur d'une classe qu'on veut changer, et une préemption qui passe
outre un PodDisruptionBudget.

Vous travaillez dans un namespace d'essai, `essai-prio`, avec deux classes
d'essai, `essai-fond` (500) et `essai-vital` (50000), et le nœud
`multi-worker2`. Le challenge porte sur d'autres classes et sur l'autre
worker : vous le ferez seul, à la fin.

Page associée : [Scheduling avancé](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/scheduling-avance/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-prioriser-et-preempter
```

Vous êtes maintenant connecté à `k8s-kind.lab`. Le lab y a créé un cluster
kind nommé `multi`, avec un control plane et deux workers, et votre kubectl le
vise.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.0 (cluster kind).

Créez le namespace et les deux classes d'essai, puis regardez les nœuds :

```bash
kubectl create namespace essai-prio; kubectl create priorityclass essai-fond --value=500; kubectl create priorityclass essai-vital --value=50000; kubectl get nodes
```

```text
namespace/essai-prio created
priorityclass.scheduling.k8s.io/essai-fond created
priorityclass.scheduling.k8s.io/essai-vital created
NAME                  STATUS   ROLES           AGE     VERSION
multi-control-plane   Ready    control-plane   3m59s   v1.37.0
multi-worker          Ready    <none>          3m48s   v1.37.0
multi-worker2         Ready    <none>          3m48s   v1.37.0
```

## ❓ Exercice 1 : une classe qui n'existe pas

Créez un Pod qui demande une classe que personne n'a créée :

```bash
kubectl run orphelin --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-prio --overrides='{"spec":{"priorityClassName":"essai-inconnue"}}' -- sleep 3600
```

```text
Error from server (Forbidden): pods "orphelin" is forbidden: no PriorityClass with name essai-inconnue was found
```

L'API refuse le Pod à la création. Le contrôleur d'admission `Priority`
cherche la classe et ne la trouve pas. Le Pod n'existe pas du tout : il n'est
pas en attente quelque part.

## ✍️ Exercice 2 : écrire la priorité à la main

Un Pod a un champ `priority`, un simple nombre. Essayez de l'écrire
vous-même :

```bash
kubectl run tricheur --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-prio --overrides='{"spec":{"priority":1000000}}' -- sleep 3600
```

```text
Error from server (Forbidden): pods "tricheur" is forbidden: the integer value of priority (1000000) must not be provided in pod spec; priority admission controller computed 0 from the given PriorityClass name
```

Refusé : ce champ est rempli par l'API à partir de la classe, jamais par
l'utilisateur. Sans quoi n'importe qui pourrait se donner la priorité la plus
haute. Créez un Pod qui passe par la classe, puis lisez les deux champs :

```bash
kubectl run normal --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-prio --overrides='{"spec":{"priorityClassName":"essai-vital"}}' -- sleep 3600; kubectl get pod normal -n essai-prio -o jsonpath='classe={.spec.priorityClassName} priorité={.spec.priority}{"\n"}'
```

```text
pod/normal created
classe=essai-vital priorité=50000
```

L'API a recopié la valeur de `essai-vital`, 50000, dans le champ `priority`.

## 🔒 Exercice 3 : la valeur d'une classe ne se change pas

Essayez de passer `essai-fond` de 500 à 700 :

```bash
kubectl patch priorityclass essai-fond --type merge -p '{"value":700}'
```

```text
The PriorityClass "essai-fond" is invalid: value: Forbidden: may not be changed in an update.
```

Refusé. La valeur est recopiée dans chaque Pod à sa création. La changer
dans la classe laisserait les anciens Pods avec l'ancienne valeur. Pour
changer une priorité, on crée une nouvelle classe, et on y fait passer les
Pods.

## ⚔️ Exercice 4 : la préemption passe outre un budget

Regardez ce que le worker `multi-worker2` a déjà réservé en CPU :

```bash
kubectl describe node multi-worker2 | grep -A4 'Allocated resources'
```

```text
Allocated resources:
  (Total limits may be over 100 percent, i.e., overcommitted.)
  Resource           Requests   Limits
  --------           --------   ------
  cpu                100m (5%)  0 (0%)
```

Calculez une part de CPU telle que trois Pods remplissent le reste du nœud.
La part est gardée dans `~/part-cpu` pour les commandes suivantes :

```bash
A=$(kubectl get node multi-worker2 -o jsonpath='{.status.allocatable.cpu}'); case $A in *m) A=${A%m};; *) A=$((A*1000));; esac; R=$(kubectl describe node multi-worker2 | awk '/Allocated resources/{f=1} f&&$1=="cpu"{print $2; exit}' | tr -d m); PART=$(( (A - R) / 3 - 10 )); echo "alloué ${A}m, déjà demandé ${R}m, part de chaque Pod : ${PART}m"; echo $PART > ~/part-cpu
```

```text
alloué 2000m, déjà demandé 100m, part de chaque Pod : 623m
```

Créez un Deployment `garde` de trois Pods de classe `essai-fond`, chacun avec
cette part, sur `multi-worker2`. Protégez-le ensuite par un
PodDisruptionBudget (PDB) qui exige trois Pods disponibles :

```bash
PART=$(cat ~/part-cpu); cat <<YAML | kubectl apply -n essai-prio -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: garde
spec:
  replicas: 3
  selector:
    matchLabels: {app: garde}
  template:
    metadata:
      labels: {app: garde}
    spec:
      priorityClassName: essai-fond
      nodeSelector: {kubernetes.io/hostname: multi-worker2}
      containers:
        - name: garde
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: [sleep, "3600"]
          resources:
            requests: {cpu: ${PART}m}
YAML
```

```text
kubectl rollout status deployment/garde -n essai-prio --timeout=120s; kubectl create poddisruptionbudget protege -n essai-prio --selector=app=garde --min-available=3; kubectl get pdb protege -n essai-prio
deployment.apps/garde created
Waiting for deployment spec update to be observed...
Waiting for deployment "garde" rollout to finish: 0 out of 3 new replicas have been updated...
Waiting for deployment "garde" rollout to finish: 0 of 3 updated replicas are available...
Waiting for deployment "garde" rollout to finish: 1 of 3 updated replicas are available...
Waiting for deployment "garde" rollout to finish: 2 of 3 updated replicas are available...
deployment "garde" successfully rolled out
poddisruptionbudget.policy/protege created
NAME      MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
protege   3               N/A               0                     0s
```

`ALLOWED DISRUPTIONS` vaut 0 : le budget interdit de retirer un seul Pod de
`garde`. Créez maintenant un Pod `vital`, de classe `essai-vital`, qui demande
la même part sur le même nœud, déjà plein :

```bash
PART=$(cat ~/part-cpu); cat <<YAML | kubectl apply -n essai-prio -f -
apiVersion: v1
kind: Pod
metadata:
  name: vital
spec:
  priorityClassName: essai-vital
  nodeSelector: {kubernetes.io/hostname: multi-worker2}
  containers:
    - name: vital
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: [sleep, "3600"]
      resources:
        requests: {cpu: ${PART}m}
YAML
```

```text
kubectl wait --for=condition=Ready pod/vital -n essai-prio --timeout=120s; kubectl get pods -n essai-prio -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName,CLASSE:.spec.priorityClassName
pod/vital created
pod/vital condition met
NOM                      ETAT      NOEUD           CLASSE
garde-69cf8f5868-5wjt9   Running   multi-worker2   essai-fond
garde-69cf8f5868-kcnjh   Pending   <none>          essai-fond
garde-69cf8f5868-njc79   Running   multi-worker2   essai-fond
normal                   Running   multi-worker2   essai-vital
vital                    Running   multi-worker2   essai-vital
```

`vital` tourne. Un Pod de `garde` a été retiré, et le Deployment en a recréé un
autre, qui reste `Pending` : il n'y a plus de place pour lui. Les événements
nomment le Pod retiré :

```bash
kubectl get events -n essai-prio --field-selector reason=Preempted -o custom-columns=OBJET:.involvedObject.name,MESSAGE:.message --no-headers | tail -2; kubectl get pdb protege -n essai-prio
```

```text
garde-69cf8f5868-cckx5   Preempted by pod 7667a9de-b1ff-410d-a3bd-8b1fe94bdcef on node multi-worker2
NAME      MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
protege   3               N/A               0                     33s
```

`Preempted by pod … on node multi-worker2`. Le budget n'a pas empêché la
préemption : le scheduler essaie de respecter les PDB, mais si aucun autre
choix ne permet de placer le Pod prioritaire, il passe outre. Un PDB protège
contre les évictions volontaires, comme un `kubectl drain`, pas contre la
préemption.

## 🧹 Nettoyage

Supprimez le namespace, les deux classes, qui n'appartiennent à aucun
namespace, et le fichier de la part :

```bash
kubectl delete namespace essai-prio; kubectl delete priorityclass essai-fond essai-vital; rm -f ~/part-cpu
```

```text
namespace "essai-prio" deleted
priorityclass.scheduling.k8s.io "essai-fond" deleted
priorityclass.scheduling.k8s.io "essai-vital" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-prioriser-et-preempter
dsoxlab check k8s-prioriser-et-preempter
```

```text
╭─ Résultat : k8s-prioriser-et-preempter ─╮
│  0 / 100 pts                            │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests        │
╰─────────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : deux classes, un nœud rempli, et un Pod urgent qui
doit s'y faire une place.

```bash
dsoxlab run k8s-prioriser-et-preempter
dsoxlab challenge k8s-prioriser-et-preempter
```
