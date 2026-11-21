# Plafonner un namespace sans bloquer ceux qui oublient de se déclarer

La leçon montre le ResourceQuota, qui plafonne ce qu'un namespace consomme,
et le LimitRange, qui borne et complète les ressources de chaque conteneur.
Ce cours ajoute des cas que la leçon ne montre pas : un quota posé alors que
le namespace le dépasse déjà, un Deployment bloqué dont l'erreur se cache
ailleurs, une borne sur l'écart entre demande et limite, un quota qui ne
compte qu'une sorte de Pods, et un quota sur le nombre d'objets.

Vous travaillez dans un namespace d'essai, `essai-quota`, avec des quotas
`plafond-*` et un LimitRange `bornes-ecart`. Le challenge porte sur un autre
namespace : vous le ferez seul, à la fin.

Page associée : [ResourceQuota et LimitRange](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/resource-quotas/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-resourcequota-limitrange
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

## ⏰ Exercice 1 : un quota posé après coup

Créez le namespace et trois Pods, qui demandent chacun 100m de CPU :

```bash
kubectl create namespace essai-quota; kubectl run avant-1 --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-quota --overrides='{"spec":{"containers":[{"name":"avant-1","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"resources":{"requests":{"cpu":"100m"},"limits":{"cpu":"100m"}}}]}}' -- sleep 3600 >/dev/null; kubectl run avant-2 --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-quota --overrides='{"spec":{"containers":[{"name":"avant-2","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"resources":{"requests":{"cpu":"100m"},"limits":{"cpu":"100m"}}}]}}' -- sleep 3600 >/dev/null; kubectl run avant-3 --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-quota --overrides='{"spec":{"containers":[{"name":"avant-3","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"resources":{"requests":{"cpu":"100m"},"limits":{"cpu":"100m"}}}]}}' -- sleep 3600 >/dev/null; kubectl get pods -n essai-quota
```

```text
namespace/essai-quota created
NAME      READY   STATUS              RESTARTS   AGE
avant-1   0/1     ContainerCreating   0          0s
avant-2   0/1     ContainerCreating   0          0s
avant-3   0/1     ContainerCreating   0          0s
```

Posez maintenant un quota de deux Pods, puis comptez les Pods :

```bash
kubectl create quota plafond-pods --hard=pods=2 -n essai-quota; sleep 3; kubectl get quota plafond-pods -n essai-quota; kubectl get pods -n essai-quota --no-headers | wc -l
```

```text
resourcequota/plafond-pods created
NAME           REQUEST     LIMIT   AGE
plafond-pods   pods: 3/2           3s
3
```

Le quota affiche `3/2` : le namespace le dépasse, et les trois Pods tournent
toujours. Un quota ne supprime rien. Il ne joue qu'à la création. Essayez
d'en créer un quatrième :

```bash
kubectl run apres --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-quota --overrides='{"spec":{"containers":[{"name":"apres","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"resources":{"requests":{"cpu":"100m"},"limits":{"cpu":"100m"}}}]}}' -- sleep 3600
```

```text
Error from server (Forbidden): pods "apres" is forbidden: exceeded quota: plafond-pods, requested: pods=1, used: pods=3, limited: pods=2
```

Refusé, avec le détail du calcul. Retirez ce quota :

```bash
kubectl delete quota plafond-pods -n essai-quota
```

```text
resourcequota "plafond-pods" deleted from essai-quota namespace
```

## 🕵️ Exercice 2 : un Deployment bloqué, l'erreur est ailleurs

Posez un quota de 500m de CPU, puis créez un Deployment de trois réplicas qui
demandent 200m chacun. La commande fabrique le Deployment, lui ajoute ses
ressources avec `kubectl set resources --local`, puis l'envoie :

```bash
kubectl create quota plafond-cpu --hard=requests.cpu=500m,limits.cpu=500m -n essai-quota; kubectl create deployment etal --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --replicas=3 -n essai-quota --dry-run=client -o yaml -- sleep 3600 | kubectl set resources --local -f - --requests=cpu=200m --limits=cpu=200m -o yaml | kubectl apply -f -; sleep 8; kubectl get deployment etal -n essai-quota; kubectl get quota plafond-cpu -n essai-quota
```

```text
resourcequota/plafond-cpu created
deployment.apps/etal created
NAME   READY   UP-TO-DATE   AVAILABLE   AGE
etal   1/3     1            1           8s
NAME          REQUEST                   LIMIT                   AGE
plafond-cpu   requests.cpu: 500m/500m   limits.cpu: 500m/500m   8s
```

`1/3`, sans un mot d'erreur. Le quota est plein : les trois Pods `avant-*`
de l'exercice 1 comptent pour 300m, et le premier Pod du Deployment pour 200m.
Le Deployment ne crée pas ses Pods lui-même : c'est son ReplicaSet. L'erreur
est donc dans les événements du ReplicaSet :

```bash
kubectl describe replicaset -n essai-quota -l app=etal | grep FailedCreate | tail -1 | cut -c1-260
```

```text
  Warning  FailedCreate      8s (x4 over 8s)  replicaset-controller  (combined from similar events): Error creating: pods "etal-8bb4cbf65-b65d9" is forbidden: exceeded quota: plafond-cpu, requested: limits.cpu=200m,requests.cpu=200m, used: limits.cpu=500m,requ
```

Quand un Deployment n'atteint pas son nombre de réplicas sans Pod en erreur,
regardez son ReplicaSet. Supprimez le Deployment, les Pods et le quota :

```bash
kubectl delete deployment etal -n essai-quota; kubectl delete pod --all -n essai-quota --wait=false >/dev/null; kubectl delete quota plafond-cpu -n essai-quota
```

```text
deployment.apps "etal" deleted from essai-quota namespace
resourcequota "plafond-cpu" deleted from essai-quota namespace
```

## 📐 Exercice 3 : borner l'écart entre demande et limite

`maxLimitRequestRatio` fixe l'écart maximal entre la limite et la demande
d'un conteneur. Avec 2, la limite ne peut pas dépasser le double de la
demande. Créez ce LimitRange, puis deux Pods : l'un demande 100m et se limite
à 200m, l'autre demande 100m et se limite à 500m.

```bash
cat <<'YAML' | kubectl apply -n essai-quota -f -
apiVersion: v1
kind: LimitRange
metadata:
  name: bornes-ecart
spec:
  limits:
    - type: Container
      maxLimitRequestRatio:
        cpu: "2"
YAML
```

```text
kubectl run raisonnable --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-quota --overrides='{"spec":{"containers":[{"name":"raisonnable","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"resources":{"requests":{"cpu":"100m"},"limits":{"cpu":"200m"}}}]}}' -- sleep 3600 >/dev/null; echo raisonnable cree; kubectl run gourmand --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-quota --overrides='{"spec":{"containers":[{"name":"gourmand","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"resources":{"requests":{"cpu":"100m"},"limits":{"cpu":"500m"}}}]}}' -- sleep 3600
limitrange/bornes-ecart created
raisonnable cree
Error from server (Forbidden): pods "gourmand" is forbidden: cpu max limit to request ratio per Container is 2, but provided ratio is 5.000000
```

Le premier passe, le second est refusé avec un rapport de 5. Cette borne
empêche un conteneur de réserver peu et de consommer beaucoup, au détriment
de ses voisins sur le nœud. Retirez le LimitRange :

```bash
kubectl delete limitrange bornes-ecart -n essai-quota
```

```text
limitrange "bornes-ecart" deleted from essai-quota namespace
```

## 🎯 Exercice 4 : un quota qui ne compte que les Pods sans ressources

Un quota peut avoir une portée (`scopes`). Avec `BestEffort`, il ne compte que
les Pods qui ne déclarent aucune ressource. Limitez ces Pods à un seul, puis
créez-en deux :

```bash
cat <<'YAML' | kubectl apply -n essai-quota -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: plafond-besteffort
spec:
  hard:
    pods: "1"
  scopes: [BestEffort]
YAML
```

```text
kubectl run nu-1 --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-quota -- sleep 3600 >/dev/null; echo nu-1 cree; kubectl run nu-2 --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-quota -- sleep 3600
resourcequota/plafond-besteffort created
nu-1 cree
Error from server (Forbidden): pods "nu-2" is forbidden: exceeded quota: plafond-besteffort, requested: pods=1, used: pods=1, limited: pods=1
```

Le second est refusé. Créez maintenant un Pod qui déclare des ressources, et
regardez la classe de qualité de service (QoS) de chaque Pod :

```bash
kubectl run vetu --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-quota --overrides='{"spec":{"containers":[{"name":"vetu","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"resources":{"requests":{"cpu":"50m"},"limits":{"cpu":"50m"}}}]}}' -- sleep 3600 >/dev/null; kubectl get quota plafond-besteffort -n essai-quota; kubectl get pods -n essai-quota -l run -o custom-columns=NOM:.metadata.name,QOS:.status.qosClass --no-headers
```

```text
NAME                 REQUEST     LIMIT   AGE
plafond-besteffort   pods: 1/1           0s
avant-1       Burstable
avant-2       Burstable
avant-3       Burstable
nu-1          BestEffort
raisonnable   Burstable
vetu          Burstable
```

`vetu` est accepté, et le quota reste à `1/1` : il ne le compte pas. Seul
`nu-1` est en `BestEffort`. Cette portée laisse passer les applications qui
se déclarent, et plafonne celles qui ne disent rien.

## 🔢 Exercice 5 : compter les objets

`count/<ressource>` plafonne un nombre d'objets. Limitez les ConfigMaps à
deux, et regardez ce que le quota compte déjà :

```bash
kubectl create quota plafond-objets --hard=count/configmaps=2 -n essai-quota; sleep 3; kubectl get quota plafond-objets -n essai-quota; kubectl get configmaps -n essai-quota
```

```text
resourcequota/plafond-objets created
NAME             REQUEST                 LIMIT   AGE
plafond-objets   count/configmaps: 1/2           3s
NAME               DATA   AGE
kube-root-ca.crt   1      16s
```

`1/2` dans un namespace où vous n'avez créé aucune ConfigMap : chaque
namespace reçoit d'office `kube-root-ca.crt`, le certificat de l'API. Créez
deux ConfigMaps :

```bash
kubectl create configmap reglages-1 -n essai-quota --from-literal=a=1 >/dev/null; echo reglages-1 cree; kubectl create configmap reglages-2 -n essai-quota --from-literal=a=2
```

```text
reglages-1 cree
error: failed to create configmap: configmaps "reglages-2" is forbidden: exceeded quota: plafond-objets, requested: count/configmaps=1, used: count/configmaps=2, limited: count/configmaps=2
```

La seconde est refusée. Pour un quota d'objets, comptez aussi ceux que le
cluster crée lui-même.

## 🧹 Nettoyage

Supprimez le namespace d'essai. Les quotas, les Pods et les ConfigMaps
partent avec lui :

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
dsoxlab reset cka-resourcequota-limitrange
dsoxlab check cka-resourcequota-limitrange
```

```text
╭─ Résultat : cka-resourcequota-limitrange ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests          │
╰───────────────────────────────────────────╯
```

0 sur 2 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un namespace à plafonner, sans bloquer les Pods qui
oublient de déclarer leurs ressources.

```bash
dsoxlab run cka-resourcequota-limitrange
dsoxlab challenge cka-resourcequota-limitrange
```
