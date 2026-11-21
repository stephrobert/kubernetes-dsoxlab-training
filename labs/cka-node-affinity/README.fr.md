# Placer avec nodeAffinity : contrainte obligatoire et préférence

La leçon montre `nodeAffinity` : une contrainte obligatoire qui choisit les
nœuds possibles, et une préférence qui les classe. Ce cours ajoute des cas que
la leçon ne montre pas : la différence entre ET et OU selon l'endroit où l'on
écrit une condition, la comparaison d'un nombre avec `Gt`, la désignation d'un
nœud par son nom avec `matchFields`, deux préférences de poids différents, et
une étiquette retirée après le placement.

Vous travaillez dans un namespace d'essai, `essai-affinite`, avec deux
étiquettes d'essai posées sur les nœuds : `essai-zone` et `essai-generation`.
Le challenge porte sur d'autres étiquettes et d'autres objets : vous le ferez
seul, à la fin.

Page associée : [Affinité, tolérances et taints](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/affinity-toleration-taint/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-node-affinity
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Créez le namespace et posez les étiquettes d'essai : le control plane est en
zone `nord`, génération 3, le worker en zone `sud`, génération 5.

```bash
kubectl create namespace essai-affinite; kubectl label node k8s-cp.lab essai-zone=nord essai-generation=3; kubectl label node k8s-w1.lab essai-zone=sud essai-generation=5; kubectl get nodes -L essai-zone,essai-generation
```

```text
namespace/essai-affinite created
node/k8s-cp.lab labeled
node/k8s-w1.lab labeled
NAME         STATUS   ROLES           AGE   VERSION   ESSAI-ZONE   ESSAI-GENERATION
k8s-cp.lab   Ready    control-plane   35h   v1.37.2   nord         3
k8s-w1.lab   Ready    <none>          35h   v1.37.2   sud          5
```

Chaque Pod de ce cours tolère la taint du control plane : sans cela, le
control plane serait toujours exclu, et les exercices ne verraient qu'un
nœud. La commande crée le Pod, attend 6 secondes, puis affiche son nom, son
état et son nœud.

## 🔀 Exercice 1 : ET dans un terme, OU entre deux termes

Créez un Pod avec un seul terme (`nodeSelectorTerms`) qui contient deux
conditions : zone `nord` et génération 5.

```bash
kubectl run et --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-affinite --overrides='{"spec":{"tolerations":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists","effect":"NoSchedule"}],"affinity":{"nodeAffinity":{"requiredDuringSchedulingIgnoredDuringExecution":{"nodeSelectorTerms":[{"matchExpressions":[{"key":"essai-zone","operator":"In","values":["nord"]},{"key":"essai-generation","operator":"In","values":["5"]}]}]}}}}}' -- sleep 3600 >/dev/null; sleep 6; kubectl get pod et -n essai-affinite -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
et    Pending   <none>
```

Créez le même Pod avec deux termes séparés, une condition chacun :

```bash
kubectl run ou --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-affinite --overrides='{"spec":{"tolerations":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists","effect":"NoSchedule"}],"affinity":{"nodeAffinity":{"requiredDuringSchedulingIgnoredDuringExecution":{"nodeSelectorTerms":[{"matchExpressions":[{"key":"essai-zone","operator":"In","values":["nord"]}]},{"matchExpressions":[{"key":"essai-generation","operator":"In","values":["5"]}]}]}}}}}' -- sleep 3600 >/dev/null; sleep 6; kubectl get pod ou -n essai-affinite -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
ou    Running   k8s-w1.lab
```

Le premier reste `Pending`, le second tourne sur le worker. Dans un même
terme, toutes les conditions doivent être vraies (ET) : aucun nœud n'est à la
fois `nord` et génération 5. Entre deux termes, un seul suffit (OU) : le
worker est génération 5. Le scheduler explique le refus du premier :

```bash
kubectl get events -n essai-affinite --field-selector involvedObject.name=et,reason=FailedScheduling -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
0/2 nodes are available: 2 node(s) didn't match Pod's node affinity/selector. preemption: 0/2 nodes are available: 2 Preemption is not helpful for scheduling.
```

## 🔢 Exercice 2 : comparer un nombre avec Gt

L'opérateur `Gt` compare une étiquette à un nombre. Demandez une génération
supérieure à 4 :

```bash
kubectl run recent --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-affinite --overrides='{"spec":{"tolerations":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists","effect":"NoSchedule"}],"affinity":{"nodeAffinity":{"requiredDuringSchedulingIgnoredDuringExecution":{"nodeSelectorTerms":[{"matchExpressions":[{"key":"essai-generation","operator":"Gt","values":["4"]}]}]}}}}}' -- sleep 3600 >/dev/null; sleep 6; kubectl get pod recent -n essai-affinite -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
recent   Running   k8s-w1.lab
```

Le Pod va sur le worker, génération 5. La valeur de l'étiquette est un texte,
mais `Gt` et `Lt` la lisent comme un entier.

## 🎯 Exercice 3 : viser un nœud par son nom avec matchFields

`matchFields` compare un champ de l'objet Node, et non une étiquette. Seul
`metadata.name` est accepté :

```bash
kubectl run nomme --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-affinite --overrides='{"spec":{"tolerations":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists","effect":"NoSchedule"}],"affinity":{"nodeAffinity":{"requiredDuringSchedulingIgnoredDuringExecution":{"nodeSelectorTerms":[{"matchFields":[{"key":"metadata.name","operator":"In","values":["k8s-cp.lab"]}]}]}}}}}' -- sleep 3600 >/dev/null; sleep 6; kubectl get pod nomme -n essai-affinite -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
nomme   Running   k8s-cp.lab
```

Le Pod est sur `k8s-cp.lab`, désigné par son nom. Contrairement à `nodeName`,
qui place le Pod sans passer par le scheduler, `matchFields` passe par lui :
les ressources et les taints sont vérifiées.

## ⚖️ Exercice 4 : deux préférences, deux poids

Créez trois Pods avec deux préférences : zone `nord` avec un poids de 10,
zone `sud` avec un poids de 90.

```bash
for i in 1 2 3; do kubectl run prefere-$i --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-affinite --overrides='{"spec":{"tolerations":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists","effect":"NoSchedule"}],"affinity":{"nodeAffinity":{"preferredDuringSchedulingIgnoredDuringExecution":[{"weight":10,"preference":{"matchExpressions":[{"key":"essai-zone","operator":"In","values":["nord"]}]}},{"weight":90,"preference":{"matchExpressions":[{"key":"essai-zone","operator":"In","values":["sud"]}]}}]}}}}' -- sleep 3600 >/dev/null; done; sleep 6; kubectl get pods -n essai-affinite -l run -o custom-columns=NOM:.metadata.name,NOEUD:.spec.nodeName --no-headers | grep prefere
```

```text
prefere-1   k8s-w1.lab
prefere-2   k8s-w1.lab
prefere-3   k8s-w1.lab
```

Les trois Pods vont sur le worker, en zone `sud`. Le scheduler ajoute le poids
de chaque préférence satisfaite à la note du nœud, et 90 l'emporte sur 10. Une
préférence n'interdit rien : si le worker était plein, les Pods iraient sur le
control plane.

## 🏷️ Exercice 5 : retirer l'étiquette après le placement

Retirez l'étiquette `essai-generation` du worker (le `-` final la supprime), et
regardez le Pod `recent`, placé à l'exercice 2 grâce à elle :

```bash
kubectl label node k8s-w1.lab essai-generation-; sleep 10; kubectl get pod recent -n essai-affinite -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
node/k8s-w1.lab unlabeled
recent   Running   k8s-w1.lab
```

Le Pod tourne toujours sur le worker. La fin du nom
`requiredDuringSchedulingIgnoredDuringExecution` le dit : la règle compte au
placement, et elle est ignorée ensuite. Recréez le Pod :

```bash
kubectl delete pod recent -n essai-affinite; kubectl run recent --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-affinite --overrides='{"spec":{"tolerations":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists","effect":"NoSchedule"}],"affinity":{"nodeAffinity":{"requiredDuringSchedulingIgnoredDuringExecution":{"nodeSelectorTerms":[{"matchExpressions":[{"key":"essai-generation","operator":"Gt","values":["4"]}]}]}}}}}' -- sleep 3600 >/dev/null; sleep 6; kubectl get pod recent -n essai-affinite -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
pod "recent" deleted from essai-affinite namespace
recent   Pending   <none>
```

Cette fois, il reste `Pending` : plus aucun nœud ne porte de génération. Une
étiquette retirée ne déplace rien, mais elle bloque le prochain placement, par
exemple quand un Deployment recrée le Pod.

## 🧹 Nettoyage

Supprimez le namespace et retirez les étiquettes d'essai des deux nœuds.
L'avertissement `label "essai-generation" not found` vient du worker, dont
l'étiquette a déjà été retirée à l'exercice 5 :

```bash
kubectl delete namespace essai-affinite; kubectl label node k8s-cp.lab essai-zone- essai-generation-; kubectl label node k8s-w1.lab essai-zone- essai-generation-; kubectl get nodes -L essai-zone,essai-generation
```

```text
namespace "essai-affinite" deleted
node/k8s-cp.lab unlabeled
label "essai-generation" not found.
node/k8s-w1.lab unlabeled
NAME         STATUS   ROLES           AGE   VERSION   ESSAI-ZONE   ESSAI-GENERATION
k8s-cp.lab   Ready    control-plane   35h   v1.37.2                
k8s-w1.lab   Ready    <none>          35h   v1.37.2                
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-node-affinity
dsoxlab check cka-node-affinity
```

```text
╭── Résultat : cka-node-affinity ───╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : des applications à placer avec des contraintes et
des préférences sur des étiquettes de nœud.

```bash
dsoxlab run cka-node-affinity
dsoxlab challenge cka-node-affinity
```
