# Appliquer une recommandation du VPA

La leçon montre le VerticalPodAutoscaler (VPA) : il observe la consommation
des Pods et recommande des `requests` de CPU et de mémoire. Ce cours ajoute
des cas que la leçon ne montre pas : un plafond posé sur la recommandation, un
VPA qui ne règle que le CPU, un conteneur exclu du calcul, et le mode
`Initial`, qui n'applique la recommandation qu'aux Pods nouvellement créés.

Vous travaillez dans un namespace d'essai, `essai-vpa`, avec un Deployment
`atelier` à deux conteneurs et un VPA du même nom. Le challenge porte sur une
autre application : vous le ferez seul, à la fin.

Page associée : [Vertical Pod Autoscaling](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/vertical-pod-scaling/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-appliquer-une-recommandation-vpa
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà. Le lab a installé
metrics-server et le VPA 1.8.1 complet : le recommender qui calcule, l'updater
qui évince, et le contrôleur d'admission qui modifie les Pods à leur création.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Créez le namespace et le Deployment `atelier`. Chaque Pod a deux conteneurs,
qui demandent chacun 10m de CPU : `application`, une boucle de calcul qui
consomme plus que cela, et `journal`, qui écrit la date chaque seconde.

```bash
kubectl create namespace essai-vpa; cat <<YAML | kubectl apply -n essai-vpa -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: atelier
spec:
  replicas: 2
  selector:
    matchLabels: {app: atelier}
  template:
    metadata:
      labels: {app: atelier}
    spec:
      containers:
        - name: application
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "while :; do i=0; while [ \$i -lt 20000 ]; do i=\$((i+1)); done; sleep 0.2; done"]
          resources:
            requests: {cpu: 10m, memory: 8Mi}
        - name: journal
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "while :; do date; sleep 1; done"]
          resources:
            requests: {cpu: 10m, memory: 8Mi}
YAML
kubectl rollout status deployment/atelier -n essai-vpa --timeout=120s
```

```text
namespace/essai-vpa created
deployment.apps/atelier created
Waiting for deployment "atelier" rollout to finish: 0 out of 2 new replicas have been updated...
Waiting for deployment "atelier" rollout to finish: 0 of 2 updated replicas are available...
Waiting for deployment "atelier" rollout to finish: 1 of 2 updated replicas are available...
deployment "atelier" successfully rolled out
```

## 🧢 Exercice 1 : plafonner, et ne régler que le CPU

Créez un VPA en mode `Off` (il recommande, il n'agit pas). Pour le conteneur
`application`, il ne doit régler que le CPU (`controlledResources`), sans
dépasser 30m (`maxAllowed`). Le conteneur `journal` est exclu (`mode: Off`).
La commande attend ensuite que la recommandation apparaisse :

```bash
cat <<'YAML' | kubectl apply -n essai-vpa -f -
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: atelier
spec:
  targetRef: {apiVersion: apps/v1, kind: Deployment, name: atelier}
  updatePolicy: {updateMode: "Off"}
  resourcePolicy:
    containerPolicies:
      - containerName: application
        controlledResources: [cpu]
        maxAllowed: {cpu: 30m}
      - containerName: journal
        mode: "Off"
YAML
for i in $(seq 1 30); do kubectl get vpa atelier -n essai-vpa -o jsonpath='{.status.recommendation}' | grep -q application && break; sleep 10; done; kubectl get vpa atelier -n essai-vpa
```

```text
verticalpodautoscaler.autoscaling.k8s.io/atelier created
NAME      MODE   CPU   MEM   PROVIDED   AGE
atelier   Off    30m         True       60s
```

La colonne `CPU` affiche 30m, et la colonne `MEM` est vide : la mémoire n'est
pas réglée. Comparez la cible appliquée et la cible sans plafond :

```bash
kubectl get vpa atelier -n essai-vpa -o jsonpath='{range .status.recommendation.containerRecommendations[*]}{.containerName}: cible={.target} non plafonnée={.uncappedTarget}{"\n"}{end}'
```

```text
application: cible={"cpu":"30m"} non plafonnée={"cpu":"109m"}
```

Le recommender aurait voulu 109m (`uncappedTarget`), le plafond ramène la
cible à 30m. `journal` n'apparaît pas du tout : il est exclu. Le plafond sert
à garder un conteneur dans le budget du nœud, quoi qu'il consomme.

## 🐣 Exercice 2 : le mode Initial n'agit qu'à la création

Passez le VPA en mode `Initial`, attendez une minute, et lisez la demande de
CPU du conteneur `application` dans chaque Pod :

```bash
kubectl patch vpa atelier -n essai-vpa --type merge -p '{"spec":{"updatePolicy":{"updateMode":"Initial"}}}'; sleep 60; kubectl get pods -n essai-vpa -o jsonpath='{range .items[*]}{.metadata.name} {.spec.containers[0].resources.requests.cpu}{"\n"}{end}'
```

```text
verticalpodautoscaler.autoscaling.k8s.io/atelier patched
atelier-84755569c8-2mwm4 10m
atelier-84755569c8-vrzjz 10m
```

Rien n'a changé : 10m partout. En mode `Initial`, le VPA n'évince jamais un
Pod qui tourne. Supprimez un des deux Pods, laissez le Deployment le recréer,
et relisez les demandes des deux conteneurs :

```bash
P=$(kubectl get pods -n essai-vpa -o jsonpath='{.items[0].metadata.name}'); kubectl delete pod $P -n essai-vpa; kubectl rollout status deployment/atelier -n essai-vpa --timeout=120s; sleep 5; kubectl get pods -n essai-vpa -o jsonpath='{range .items[*]}{.metadata.name} application={.spec.containers[0].resources.requests} journal={.spec.containers[1].resources.requests} annotation={.metadata.annotations.vpaUpdates}{"\n"}{end}'
```

```text
pod "atelier-84755569c8-2mwm4" deleted from essai-vpa namespace
deployment "atelier" successfully rolled out
atelier-84755569c8-p74b8 application={"cpu":"30m","memory":"8Mi"} journal={"cpu":"10m","memory":"8Mi"} annotation=Pod resources updated by atelier: container 0: cpu request
atelier-84755569c8-vrzjz application={"cpu":"10m","memory":"8Mi"} journal={"cpu":"10m","memory":"8Mi"} annotation=
```

Le nouveau Pod a reçu 30m pour `application`, et l'annotation laissée par le
contrôleur d'admission du VPA le confirme. `journal` garde ses 10m, comme sa
mémoire : seules les ressources contrôlées changent. L'ancien Pod est
toujours à 10m. Regardez enfin le gabarit du Deployment :

```bash
kubectl get deployment atelier -n essai-vpa -o jsonpath='gabarit du Deployment : {.spec.template.spec.containers[0].resources.requests}{"\n"}'
```

```text
gabarit du Deployment : {"cpu":"10m","memory":"8Mi"}
```

Toujours 10m. Le VPA modifie les Pods au moment de leur création, jamais le
Deployment. Pour rendre une recommandation durable, il faut la reporter dans
le Deployment lui-même.

## 🧹 Nettoyage

Supprimez le namespace d'essai. Le VPA et le Deployment partent avec lui :

```bash
kubectl delete namespace essai-vpa
```

```text
namespace "essai-vpa" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-appliquer-une-recommandation-vpa
dsoxlab check k8s-appliquer-une-recommandation-vpa
```

```text
╭─ Résultat : k8s-appliquer-une-recommandation-vpa ─╮
│  0 / 100 pts                                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests                  │
╰───────────────────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une recommandation à obtenir, puis à appliquer
vous-même à une application, sans qu'aucun Pod soit évincé.

```bash
dsoxlab run k8s-appliquer-une-recommandation-vpa
dsoxlab challenge k8s-appliquer-une-recommandation-vpa
```
