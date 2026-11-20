# Remonter d'un Pod à son Deployment

Un **Deployment** ne crée pas ses Pods lui-même. Il crée un **ReplicaSet**, un
objet dont le seul travail est de garder le bon nombre de Pods, et c'est lui
qui crée les Pods. Chaque objet garde la trace de celui qui l'a créé, son
**propriétaire**. La leçon suit cette chaîne sur un Deployment qu'elle crée.
Ce cours part d'un nom de Pod seul, montre des Pods qui ne viennent pas d'un
ReplicaSet, retire un Pod de son ReplicaSet, puis diagnostique un
ReplicaSet qui n'arrive pas à créer ses Pods.

Vous travaillez dans deux namespaces d'essai, `essai-rs` et `essai-quota`. Le
challenge vous demandera de faire le même genre de lecture sur d'autres
objets : vous le ferez seul, à la fin.

Page associée : [ReplicaSet Kubernetes : ce que crée un Deployment](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/replicasets/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-lire-les-replicasets
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`boutique` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine les
19 et 20 novembre 2026.

## 📚 Exercice 1 : remonter d'un Pod jusqu'à son Deployment

Vous ne connaissez souvent qu'un nom de Pod, lu dans une alerte ou un
journal. Partez d'un Pod `coredns`, le service de noms du cluster, et
remontez la chaîne des propriétaires. Le champ `ownerReferences` nomme le
propriétaire d'un objet ; la variable `OWN` garde le chemin à afficher :

```bash
OWN='{.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}{"\n"}'
P=$(kubectl get pods -n kube-system -l k8s-app=kube-dns -o jsonpath='{.items[0].metadata.name}')
echo $P
kubectl get pod $P -n kube-system -o jsonpath="$OWN"
```

```text
coredns-559f6c778d-jwhr5
ReplicaSet/coredns-559f6c778d
```

Le Pod appartient à un ReplicaSet. Remontez d'un étage, puis encore d'un :

```bash
kubectl get replicaset coredns-559f6c778d -n kube-system -o jsonpath="$OWN"
kubectl get deployment coredns -n kube-system -o jsonpath='{.metadata.ownerReferences}{"\n"}'
```

```text
Deployment/coredns
```

Le ReplicaSet appartient au Deployment `coredns`. La dernière commande
n'affiche qu'une ligne vide : le Deployment n'a pas de propriétaire, c'est le
haut de la chaîne. Le nom du Pod la résumait déjà :
`coredns-559f6c778d-jwhr5`, c'est le Deployment, puis l'empreinte du
ReplicaSet, puis un suffixe tiré au hasard.

## 📚 Exercice 2 : voir un Pod qui n'a pas de ReplicaSet

Tous les Pods ne viennent pas d'un ReplicaSet. Faites la même lecture sur un
Pod `kube-proxy` et sur le Pod `etcd` :

```bash
K=$(kubectl get pods -n kube-system -l k8s-app=kube-proxy -o jsonpath='{.items[0].metadata.name}')
kubectl get pod $K -n kube-system -o jsonpath="$OWN"
E=$(kubectl get pods -n kube-system -l component=etcd -o jsonpath='{.items[0].metadata.name}')
kubectl get pod $E -n kube-system -o jsonpath="$OWN"
kubectl get replicaset -n kube-system
```

```text
DaemonSet/kube-proxy
Node/boutique-control-plane
NAME                 DESIRED   CURRENT   READY   AGE
coredns-559f6c778d   2         2         2       77m
```

`kube-proxy` appartient à un **DaemonSet**, un objet qui place un Pod sur
chaque nœud, sans ReplicaSet. `etcd` est rattaché au nœud lui-même : c'est un
Pod que le kubelet lance à partir d'un fichier posé sur le nœud. Le namespace
`kube-system` ne compte donc qu'un ReplicaSet, celui de `coredns`. Remonter
d'un Pod ne mène pas toujours à un Deployment.

## 📚 Exercice 3 : retirer un Pod de son ReplicaSet

Un ReplicaSet reconnaît ses Pods à leurs **étiquettes** (labels), pas à leur
nom. Créez un Deployment de trois Pods, et affichez leurs étiquettes :

```bash
kubectl create namespace essai-rs
kubectl create deployment catalogue \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  --replicas=3 -n essai-rs
kubectl rollout status deployment/catalogue -n essai-rs --timeout=120s
kubectl get pods -n essai-rs --show-labels
```

```text title="Extrait de la sortie"
namespace/essai-rs created
deployment.apps/catalogue created
deployment "catalogue" successfully rolled out
NAME                        READY   STATUS    RESTARTS   AGE   LABELS
catalogue-75867bdb5-5gv8j   1/1     Running   0          1s    app=catalogue,pod-template-hash=75867bdb5
catalogue-75867bdb5-jd9c8   1/1     Running   0          1s    app=catalogue,pod-template-hash=75867bdb5
catalogue-75867bdb5-xp9nv   1/1     Running   0          1s    app=catalogue,pod-template-hash=75867bdb5
```

Retirez l'étiquette `app` d'un des Pods. `kubectl label` pose ou retire une
étiquette, et le `-` final veut dire « retirer » ; la leçon sur les labels la
détaille plus loin :

```bash
X=$(kubectl get pods -n essai-rs -l app=catalogue -o jsonpath='{.items[0].metadata.name}')
kubectl label pod $X -n essai-rs app-
kubectl get pods -n essai-rs --show-labels
```

```text
pod/catalogue-75867bdb5-5gv8j unlabeled
NAME                        READY   STATUS    RESTARTS   AGE   LABELS
catalogue-75867bdb5-5gv8j   1/1     Running   0          6s    pod-template-hash=75867bdb5
catalogue-75867bdb5-jd9c8   1/1     Running   0          6s    app=catalogue,pod-template-hash=75867bdb5
catalogue-75867bdb5-kxt5g   1/1     Running   0          5s    app=catalogue,pod-template-hash=75867bdb5
catalogue-75867bdb5-xp9nv   1/1     Running   0          6s    app=catalogue,pod-template-hash=75867bdb5
```

Quatre Pods tournent maintenant. Le ReplicaSet ne compte plus `5gv8j` parmi
les siens : il n'en voyait que deux, et il en a créé un troisième, `kxt5g`.
Le Pod `5gv8j`, lui, continue de tourner. Lisez son propriétaire :

```bash
kubectl get pod $X -n essai-rs -o jsonpath='{.metadata.ownerReferences}{"\n"}'
kubectl get replicaset -n essai-rs
```

```text

NAME                  DESIRED   CURRENT   READY   AGE
catalogue-75867bdb5   3         3         3       6s
```

Ligne vide : le Pod n'a plus de propriétaire. Plus aucun contrôleur ne le
recréera s'il tombe, ni ne le supprimera. Le ReplicaSet compte toujours trois
Pods, sans lui.

## 📚 Exercice 4 : remplacer les Pods sans changer l'image

`kubectl rollout restart` fait remplacer tous les Pods d'un Deployment, sans
rien changer d'autre. Lancez-le, puis regardez les ReplicaSets :

```bash
kubectl rollout restart deployment/catalogue -n essai-rs
kubectl rollout status deployment/catalogue -n essai-rs --timeout=120s
kubectl get replicaset -n essai-rs -o custom-columns='NOM:.metadata.name,VOULUS:.spec.replicas,REVISION:.metadata.annotations.deployment\.kubernetes\.io/revision'
```

```text title="Extrait de la sortie"
deployment.apps/catalogue restarted
deployment "catalogue" successfully rolled out
NOM                   VOULUS   REVISION
catalogue-75867bdb5   0        1
catalogue-c4bb56c49   3        2
```

Un second ReplicaSet est apparu, comme pour une nouvelle image, et le premier
est gardé à zéro. Pourtant l'image n'a pas changé. Regardez ce que `restart`
a modifié dans le modèle de Pod :

```bash
kubectl get deployment catalogue -n essai-rs -o jsonpath='{.spec.template.metadata.annotations}{"\n"}'
kubectl get pods -n essai-rs
```

```text
{"kubectl.kubernetes.io/restartedAt":"2026-11-20T08:19:47Z"}
NAME                        READY   STATUS        RESTARTS   AGE
catalogue-75867bdb5-5gv8j   1/1     Running       0          8s
catalogue-75867bdb5-jd9c8   1/1     Terminating   0          8s
catalogue-c4bb56c49-bztv4   1/1     Running       0          1s
catalogue-c4bb56c49-cxmcq   1/1     Running       0          2s
catalogue-c4bb56c49-jq6hd   1/1     Running       0          1s
```

`restart` pose une annotation datée dans le modèle de Pod. Le modèle change,
donc son empreinte change, donc le Deployment crée un ReplicaSet. Le Pod
`5gv8j` de l'exercice 3 tourne toujours : sans propriétaire, il n'appartient à
aucun ReplicaSet, et le redémarrage ne l'a pas touché. Supprimez ce
namespace, vous n'en avez plus besoin :

```bash
kubectl delete namespace essai-rs
```

```text
namespace "essai-rs" deleted
```

## 📚 Exercice 5 : diagnostiquer un ReplicaSet bloqué

Un **quota** limite ce qu'un namespace a le droit de contenir ; la leçon sur
les quotas, bien plus loin dans le parcours, le détaille. Créez un namespace
limité à un seul Pod, puis un Deployment qui en demande deux :

```bash
kubectl create namespace essai-quota
kubectl create quota plafond --hard=pods=1 -n essai-quota
kubectl create deployment borne \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  --replicas=2 -n essai-quota
sleep 10
kubectl get deployment borne -n essai-quota
kubectl get replicaset -n essai-quota
```

```text
namespace/essai-quota created
resourcequota/plafond created
deployment.apps/borne created
NAME    READY   UP-TO-DATE   AVAILABLE   AGE
borne   1/2     1            1           10s
NAME               DESIRED   CURRENT   READY   AGE
borne-6f65f67d68   2         1         1       10s
```

Le ReplicaSet veut 2 Pods (`DESIRED`) mais n'en a qu'un (`CURRENT`). Le Pod
manquant n'existe pas, donc il n'y a aucun Pod à décrire. Remontez d'un
étage : c'est le ReplicaSet qui a essayé de le créer, et ses événements disent
pourquoi il a échoué :

```bash
kubectl describe replicaset -n essai-quota -l app=borne | sed -n '/^Events:/,$p'
```

```text title="Extrait de la sortie"
Events:
  Type     Reason            Age   From                   Message
  ----     ------            ----  ----                   -------
  Normal   SuccessfulCreate  10s   replicaset-controller  Created pod: borne-6f65f67d68-rdj78
  Warning  FailedCreate      10s   replicaset-controller  Error creating: pods "borne-6f65f67d68-m7whr" is forbidden: exceeded quota: plafond, requested: pods=1, used: pods=1, limited: pods=1
  Warning  FailedCreate      10s   replicaset-controller  Error creating: pods "borne-6f65f67d68-ngtpf" is forbidden: exceeded quota: plafond, requested: pods=1, used: pods=1, limited: pods=1
```

`FailedCreate` donne la cause : le quota `plafond` est atteint
(`used: pods=1, limited: pods=1`). Le ReplicaSet a réessayé plusieurs fois, et
la liste complète compte une dizaine de lignes identiques.

## 📚 Exercice 6 : lever la cause et voir le ReplicaSet réessayer

Relevez le quota à trois Pods, sans toucher au Deployment :

```bash
kubectl patch quota plafond -n essai-quota --type=merge -p '{"spec":{"hard":{"pods":"3"}}}'
kubectl get quota plafond -n essai-quota
kubectl wait --for=condition=Available deployment/borne -n essai-quota --timeout=180s
kubectl get deployment borne -n essai-quota
```

```text
resourcequota/plafond patched
NAME      REQUEST     LIMIT   AGE
plafond   pods: 1/3           10s
deployment.apps/borne condition met
NAME    READY   UP-TO-DATE   AVAILABLE   AGE
borne   2/2     2            2           11s
```

Vous n'avez rien relancé : le ReplicaSet réessaie tout seul tant que la
création échoue, et le second Pod est apparu dès que le quota l'a permis.
Attention, il attend un peu plus longtemps après chaque échec : sur un
ReplicaSet bloqué depuis longtemps, la reprise peut prendre une minute ou
plus.

## 🧹 Nettoyage

Supprimez d'abord ce qui reste des exercices : le namespace `essai-quota`.
Le namespace `essai-rs` est déjà supprimé.

```bash
kubectl delete namespace essai-quota
```

```text
namespace "essai-quota" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-lire-les-replicasets
dsoxlab check k8s-lire-les-replicasets
```

```text
╭─ Résultat : k8s-lire-les-replicasets ─╮
│  0 / 100 pts                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests      │
╰───────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : retrouver les ReplicaSets d'une application mise à
jour, puis diagnostiquer et réparer un Deployment qui n'a aucun Pod.

```bash
dsoxlab run k8s-lire-les-replicasets
dsoxlab challenge k8s-lire-les-replicasets
```
