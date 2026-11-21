# Faire monter en charge automatiquement avec un HorizontalPodAutoscaler

La leçon montre un HorizontalPodAutoscaler (HPA) qui ajoute des réplicas
quand la consommation de CPU monte. Ce cours ajoute des cas que la leçon ne
montre pas : un minimum de réplicas appliqué sans aucune charge, un
`kubectl scale` que le HPA défait, une cible en valeur absolue de mémoire, et
un conteneur annexe qui fausse la mesure, corrigé par une métrique par
conteneur.

Vous travaillez dans un namespace d'essai, `essai-hpa`, avec deux
Deployments, `guichet` et `mixte`. Le challenge porte sur une autre
application : vous le ferez seul, à la fin.

Page associée : [Horizontal Pod Autoscaling](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/horizontal-pod-scaling/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-hpa-autoscaling
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà. Le lab a installé
metrics-server, qui fournit au HPA la consommation des Pods.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Créez le namespace et un Deployment `guichet` à un réplica, avec des
demandes et des limites de CPU et de mémoire. Un HPA calcule ses pourcentages
à partir des demandes : sans elles, il ne peut rien mesurer en pourcentage.

```bash
kubectl create namespace essai-hpa; kubectl create deployment guichet --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb --replicas=1 -n essai-hpa >/dev/null; kubectl set resources deployment guichet -n essai-hpa --requests=cpu=50m,memory=32Mi --limits=cpu=200m,memory=64Mi >/dev/null; kubectl rollout status deployment/guichet -n essai-hpa --timeout=120s
```

```text
namespace/essai-hpa created
Waiting for deployment "guichet" rollout to finish: 0 out of 1 new replicas have been updated...
Waiting for deployment "guichet" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "guichet" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "guichet" rollout to finish: 1 old replicas are pending termination...
deployment "guichet" successfully rolled out
```

## ⬆️ Exercice 1 : minReplicas monte sans attendre la charge

Créez un HPA sur `guichet`, avec un minimum de 3 réplicas et une cible de
100 Mi de mémoire par Pod, très au-dessus de ce que nginx consomme :

```bash
cat <<'YAML' | kubectl apply -n essai-hpa -f -
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: guichet
spec:
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: guichet}
  minReplicas: 3
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: memory
        target: {type: AverageValue, averageValue: 100Mi}
YAML
sleep 20; kubectl get deployment guichet -n essai-hpa; kubectl get hpa guichet -n essai-hpa
```

```text
horizontalpodautoscaler.autoscaling/guichet created
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
guichet   3/3     3            3           21s
NAME      REFERENCE            TARGETS                MINPODS   MAXPODS   REPLICAS   AGE
guichet   Deployment/guichet   memory: 3332Ki/100Mi   3         5         3          20s
```

Le Deployment est passé de 1 à 3 réplicas alors qu'aucune charge ne le
justifie : la mémoire moyenne (3332 Ki) est loin de la cible. `minReplicas`
est un plancher que le HPA applique dès sa création.

## ↩️ Exercice 2 : un kubectl scale que le HPA défait

Ramenez le Deployment à un réplica à la main, puis regardez-le 30 secondes
plus tard :

```bash
kubectl scale deployment guichet -n essai-hpa --replicas=1; kubectl get deployment guichet -n essai-hpa; sleep 30; kubectl get deployment guichet -n essai-hpa
```

```text
deployment.apps/guichet scaled
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
guichet   3/1     3            3           21s
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
guichet   3/3     3            3           51s
```

Juste après la commande, le Deployment demande un réplica, et deux Pods sont
en train de s'arrêter. Trente secondes plus tard, il en a de nouveau 3. Les
événements du HPA disent pourquoi :

```bash
kubectl get events -n essai-hpa --field-selector involvedObject.kind=HorizontalPodAutoscaler,involvedObject.name=guichet,reason=SuccessfulRescale -o custom-columns=RAISON:.reason,MESSAGE:.message --no-headers
```

```text
SuccessfulRescale   New size: 3; reason: Current number of replicas below Spec.MinReplicas
```

Un Deployment piloté par un HPA ne se règle plus à la main : le HPA reprend la
main à son passage suivant. Pour changer le nombre de réplicas, changez
`minReplicas` et `maxReplicas`.

## 📦 Exercice 3 : une cible en valeur moyenne de mémoire

Remplacez le HPA par un HPA de 1 à 4 réplicas, qui vise 2 Mi de mémoire en
moyenne par Pod (`AverageValue`), puis regardez-le une minute plus tard :

```bash
kubectl delete hpa guichet -n essai-hpa; cat <<'YAML' | kubectl apply -n essai-hpa -f -
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: guichet
spec:
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: guichet}
  minReplicas: 1
  maxReplicas: 4
  metrics:
    - type: Resource
      resource:
        name: memory
        target: {type: AverageValue, averageValue: 2Mi}
YAML
sleep 60; kubectl get hpa guichet -n essai-hpa; kubectl top pods -n essai-hpa
```

```text
horizontalpodautoscaler.autoscaling "guichet" deleted from essai-hpa namespace
horizontalpodautoscaler.autoscaling/guichet created
NAME      REFERENCE            TARGETS              MINPODS   MAXPODS   REPLICAS   AGE
guichet   Deployment/guichet   memory: 3350Ki/2Mi   1         4         4          60s
NAME                       CPU(cores)   MEMORY(bytes)   
guichet-6f6b6549d8-484hw   0m           3Mi             
guichet-6f6b6549d8-6qgnc   0m           3Mi             
guichet-6f6b6549d8-99gfl   0m           3Mi             
guichet-6f6b6549d8-w4pq7   0m           3Mi             
```

Le HPA est monté au maximum, 4. Chaque Pod nginx consomme environ 3 Mi, et
ajouter des Pods ne fait pas baisser la mémoire de chacun : la cible ne sera
jamais atteinte. Une cible de mémoire n'a de sens que si la consommation de
chaque Pod baisse quand la charge se répartit.

## 🔍 Exercice 4 : un conteneur annexe fausse la mesure

Créez un Deployment `mixte` dont chaque Pod a deux conteneurs : `application`
(nginx, au repos) et `compteur`, une boucle qui consomme tout le CPU qu'on lui
laisse. Ajoutez un HPA à 60 % de CPU, et regardez-le après 75 secondes :

```bash
cat <<YAML | kubectl apply -n essai-hpa -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mixte
spec:
  replicas: 1
  selector:
    matchLabels: {app: mixte}
  template:
    metadata:
      labels: {app: mixte}
    spec:
      containers:
        - name: application
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          resources:
            requests: {cpu: 50m}
            limits: {cpu: 100m}
        - name: compteur
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "while :; do :; done"]
          resources:
            requests: {cpu: 50m}
            limits: {cpu: 100m}
YAML
kubectl rollout status deployment/mixte -n essai-hpa --timeout=120s; kubectl autoscale deployment mixte -n essai-hpa --min=1 --max=4 --cpu=60%; sleep 75; kubectl get hpa mixte -n essai-hpa; kubectl top pods -n essai-hpa -l app=mixte --containers
```

```text
deployment.apps/mixte created
Waiting for deployment "mixte" rollout to finish: 0 out of 1 new replicas have been updated...
Waiting for deployment "mixte" rollout to finish: 0 of 1 updated replicas are available...
deployment "mixte" successfully rolled out
horizontalpodautoscaler.autoscaling/mixte autoscaled
NAME    REFERENCE          TARGETS         MINPODS   MAXPODS   REPLICAS   AGE
mixte   Deployment/mixte   cpu: 100%/60%   1         4         2          75s
POD                      NAME          CPU(cores)   MEMORY(bytes)   
mixte-5bc776945d-j6zgc   application   0m           3Mi             
mixte-5bc776945d-j6zgc   compteur      101m         0Mi             
mixte-5bc776945d-nww54   application   0m           3Mi             
mixte-5bc776945d-nww54   compteur      100m         0Mi             
```

Le HPA mesure 101 % et a doublé les réplicas. Pourtant, l'application est au
repos (0m) : c'est `compteur` qui consomme. Une métrique `Resource` additionne
tous les conteneurs du Pod. Remplacez-la par une métrique `ContainerResource`,
qui ne mesure que le conteneur `application`. Le nouveau HPA porte un autre
nom : le contrôleur garde en mémoire les recommandations récentes d'un HPA par
son nom, et un HPA recréé sous le même nom en hériterait.

```bash
kubectl delete hpa mixte -n essai-hpa; kubectl scale deployment mixte -n essai-hpa --replicas=1; cat <<'YAML' | kubectl apply -n essai-hpa -f -
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mixte-application
spec:
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: mixte}
  minReplicas: 1
  maxReplicas: 4
  metrics:
    - type: ContainerResource
      containerResource:
        name: cpu
        container: application
        target: {type: Utilization, averageUtilization: 60}
YAML
sleep 75; kubectl get hpa mixte-application -n essai-hpa; kubectl get deployment mixte -n essai-hpa
```

```text
horizontalpodautoscaler.autoscaling "mixte" deleted from essai-hpa namespace
deployment.apps/mixte scaled
horizontalpodautoscaler.autoscaling/mixte-application created
NAME                REFERENCE          TARGETS       MINPODS   MAXPODS   REPLICAS   AGE
mixte-application   Deployment/mixte   cpu: 0%/60%   1         4         1          75s
NAME    READY   UP-TO-DATE   AVAILABLE   AGE
mixte   1/1     1            1           2m32s
```

0 % : le HPA ne voit plus que l'application, et le Deployment est revenu à un
réplica. Quand un Pod contient des conteneurs annexes, mesurez le conteneur
qui porte la charge.

## 🧹 Nettoyage

Supprimez le namespace d'essai. Les HPA et les Deployments partent avec lui :

```bash
kubectl delete namespace essai-hpa
```

```text
namespace "essai-hpa" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-hpa-autoscaling
dsoxlab check cka-hpa-autoscaling
```

```text
╭─ Résultat : cka-hpa-autoscaling ──╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une application à faire monter en charge
automatiquement, et une charge pour le prouver.

```bash
dsoxlab run cka-hpa-autoscaling
dsoxlab challenge cka-hpa-autoscaling
```
