# Réserver un nœud : taint, tolérance et nodeSelector

La leçon montre un taint, qui écarte les Pods d'un nœud, et une tolérance,
qui permet à un Pod d'y aller quand même. Ce cours essaie chaque effet de
taint sur le worker et ajoute des cas que la leçon ne montre pas : les
tolérances que chaque Pod reçoit sans les avoir écrites, un taint qui
n'expulse personne, une tolérance qui vise le mauvais effet, une tolérance
universelle, un taint qui expulse, un taint qui n'est qu'une préférence, et le
taint que pose `kubectl cordon`.

Vous travaillez dans un namespace d'essai, `essai-taint`, avec un taint
d'essai, `essai-maintenance=oui`, posé et retiré sur le worker `k8s-w1.lab`.
Le challenge porte sur un autre taint et d'autres objets : vous le ferez seul,
à la fin.

Page associée : [Affinité, tolérances et taints](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/affinity-toleration-taint/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-taints-tolerations-placement
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Regardez d'abord les taints des deux nœuds :

```bash
kubectl get nodes -o custom-columns=NOM:.metadata.name,TAINTS:.spec.taints
```

```text
NOM          TAINTS
k8s-cp.lab   <none>
k8s-w1.lab   <none>
```

Aucun taint, pas même sur le control plane : sur ce cluster de lab, il a été
retiré pour que les Pods puissent s'y placer. Pour que les taints d'essai se
voient, les Pods de ce cours demandent le worker par un `nodeSelector` sur
l'étiquette `kubernetes.io/hostname`. Sans cela, le scheduler les enverrait
simplement sur le control plane.

Créez le namespace et un Pod `resident`, placé d'office sur le worker :

```bash
kubectl create namespace essai-taint; kubectl run resident --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-taint --overrides='{"spec":{"nodeName":"k8s-w1.lab"}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/resident -n essai-taint --timeout=120s
```

```text
namespace/essai-taint created
pod/resident created
pod/resident condition met
```

## 🎁 Exercice 1 : les tolérances qu'un Pod reçoit d'office

Vous n'avez écrit aucune tolérance pour `resident`. Lisez pourtant les
siennes :

```bash
kubectl get pod resident -n essai-taint -o jsonpath='{range .spec.tolerations[*]}{.key} {.operator} {.effect} {.tolerationSeconds}{"\n"}{end}'
```

```text
node.kubernetes.io/not-ready Exists NoExecute 300
node.kubernetes.io/unreachable Exists NoExecute 300
```

L'API en a ajouté deux. Quand un nœud devient injoignable ou n'est plus prêt,
Kubernetes lui pose un taint `NoExecute`. Ces tolérances laissent le Pod en
place 300 secondes avant de l'expulser : c'est le délai avant qu'un Pod quitte
un nœud tombé.

## 🚧 Exercice 2 : NoSchedule n'expulse personne

Posez un taint `NoSchedule` sur le worker :

```bash
kubectl taint node k8s-w1.lab essai-maintenance=oui:NoSchedule; sleep 10; kubectl get pods -n essai-taint -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
node/k8s-w1.lab tainted
resident   Running   k8s-w1.lab
```

`resident` tourne toujours. Créez un Pod qui demande le worker :

```bash
kubectl run arrivant --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-taint --overrides='{"spec":{"nodeSelector":{"kubernetes.io/hostname":"k8s-w1.lab"}}}' -- sleep 3600; sleep 8; kubectl get pods -n essai-taint -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
pod/arrivant created
arrivant   Pending   <none>
resident   Running   k8s-w1.lab
```

`arrivant` reste `Pending`. `NoSchedule` refuse les nouveaux Pods, mais ne
touche pas à ceux qui tournent déjà.

## 🎯 Exercice 3 : une tolérance qui vise le mauvais effet

Créez un Pod qui tolère bien la clé et la valeur du taint, mais avec l'effet
`NoExecute` au lieu de `NoSchedule` :

```bash
kubectl run mal-tolerant --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-taint --overrides='{"spec":{"nodeSelector":{"kubernetes.io/hostname":"k8s-w1.lab"},"tolerations":[{"key":"essai-maintenance","operator":"Equal","value":"oui","effect":"NoExecute"}]}}' -- sleep 3600; sleep 8; kubectl get pods -n essai-taint -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
pod/mal-tolerant created
arrivant       Pending   <none>
mal-tolerant   Pending   <none>
resident       Running   k8s-w1.lab
```

```bash
kubectl get events -n essai-taint --field-selector involvedObject.name=mal-tolerant,reason=FailedScheduling -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
0/2 nodes are available: 1 node(s) didn't match Pod's node affinity/selector, 1 node(s) had untolerated taint(s). preemption: 0/2 nodes are available: 2 Preemption is not helpful for scheduling.
```

`mal-tolerant` reste `Pending`, comme `arrivant`. Une tolérance doit
correspondre à la clé, à la valeur et à l'effet du taint. Le scheduler parle
d'un taint non toléré sur un nœud, et d'un sélecteur non satisfait sur
l'autre.

## 🃏 Exercice 4 : une tolérance universelle

Une tolérance avec `operator: Exists` et sans clé tolère tous les taints :

```bash
kubectl run tout-tolerant --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-taint --overrides='{"spec":{"nodeSelector":{"kubernetes.io/hostname":"k8s-w1.lab"},"tolerations":[{"operator":"Exists"}]}}' -- sleep 3600; sleep 8; kubectl get pods -n essai-taint -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
pod/tout-tolerant created
arrivant        Pending   <none>
mal-tolerant    Pending   <none>
resident        Running   k8s-w1.lab
tout-tolerant   Running   k8s-w1.lab
```

`tout-tolerant` tourne sur le worker. C'est la tolérance des agents qui
doivent être partout, comme ceux du réseau. Sur un Pod ordinaire, elle le
laisse aussi sur un nœud qu'on veut vider.

## 🚪 Exercice 5 : NoExecute expulse

Remplacez le taint par un taint `NoExecute`, après avoir supprimé les deux
Pods en attente. La commande attend 45 secondes, le temps que `resident`
s'arrête :

```bash
kubectl taint node k8s-w1.lab essai-maintenance=oui:NoSchedule-; kubectl delete pod arrivant mal-tolerant -n essai-taint --wait=false >/dev/null; kubectl taint node k8s-w1.lab essai-maintenance=oui:NoExecute; sleep 45; kubectl get pods -n essai-taint -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
node/k8s-w1.lab untainted
node/k8s-w1.lab tainted
tout-tolerant   Running   k8s-w1.lab
```

`resident` a disparu, `tout-tolerant` est resté. Les événements de
`resident` disent qui l'a expulsé :

```bash
kubectl get events -n essai-taint --field-selector involvedObject.name=resident -o custom-columns=RAISON:.reason,MESSAGE:.message --no-headers | grep -E 'TaintManager|Killing'
```

```text
TaintManagerEviction   Marking for deletion Pod essai-taint/resident
Killing                Stopping container resident
```

`TaintManagerEviction` : le contrôleur des taints a supprimé le Pod. Un Pod
sans contrôleur ne revient pas. Un Pod d'un Deployment serait recréé
ailleurs. Avant de poser un `NoExecute`, vérifiez donc ce qui tourne sur le
nœud.

## 🌤️ Exercice 6 : PreferNoSchedule, une préférence

Remplacez le taint par un taint `PreferNoSchedule`, et créez un Pod qui
demande le worker, sans tolérance :

```bash
kubectl taint node k8s-w1.lab essai-maintenance=oui:NoExecute-; kubectl taint node k8s-w1.lab essai-maintenance=oui:PreferNoSchedule; kubectl run souple --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-taint --overrides='{"spec":{"nodeSelector":{"kubernetes.io/hostname":"k8s-w1.lab"}}}' -- sleep 3600; sleep 8; kubectl get pods -n essai-taint -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
node/k8s-w1.lab untainted
node/k8s-w1.lab tainted
pod/souple created
souple          Running   k8s-w1.lab
tout-tolerant   Running   k8s-w1.lab
```

`souple` tourne sur le worker. `PreferNoSchedule` demande au scheduler
d'éviter le nœud quand il a le choix. Ici, le `nodeSelector` ne lui laisse
pas le choix.

## 🔒 Exercice 7 : cordon est un taint

Retirez le taint d'essai, puis marquez le worker comme non planifiable avec
`kubectl cordon`, et lisez ses taints :

```bash
kubectl taint node k8s-w1.lab essai-maintenance=oui:PreferNoSchedule-; kubectl cordon k8s-w1.lab; kubectl get node k8s-w1.lab -o jsonpath='{range .spec.taints[*]}{.key}={.value}:{.effect}{"\n"}{end}'
```

```text
node/k8s-w1.lab untainted
node/k8s-w1.lab cordoned
node.kubernetes.io/unschedulable=:NoSchedule
```

`cordon` pose le taint `node.kubernetes.io/unschedulable:NoSchedule`. Il a donc
le même effet qu'à l'exercice 2 : les Pods en place restent, les nouveaux sont
refusés. `uncordon` le retire :

```bash
kubectl uncordon k8s-w1.lab; kubectl get node k8s-w1.lab -o jsonpath='taints={.spec.taints}{"\n"}'
```

```text
node/k8s-w1.lab uncordoned
taints=
```

## 🧹 Nettoyage

Supprimez le namespace d'essai et vérifiez qu'il ne reste aucun taint sur le
worker :

```bash
kubectl delete namespace essai-taint; kubectl get node k8s-w1.lab -o jsonpath='taints={.spec.taints}{"\n"}'
```

```text
namespace "essai-taint" deleted
taints=
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-taints-tolerations-placement
dsoxlab check cka-taints-tolerations-placement
```

```text
╭─ Résultat : cka-taints-tolerations-placement ─╮
│  0 / 100 pts                                  │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests              │
╰───────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un nœud à réserver à la production, une application
qui y va, et une autre qui n'y va pas.

```bash
dsoxlab run cka-taints-tolerations-placement
dsoxlab challenge cka-taints-tolerations-placement
```
