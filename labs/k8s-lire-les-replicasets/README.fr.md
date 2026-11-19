# Remonter d'un Pod à son Deployment

Un **Deployment** ne crée pas ses Pods lui-même. Il crée un **ReplicaSet**, un
objet dont le seul travail est de garder le bon nombre de Pods, et c'est lui
qui crée les Pods. Chaque objet garde la trace de celui qui l'a créé, son
**propriétaire**. Dans ce cours, vous suivez cette chaîne, vous voyez ce que
devient un ReplicaSet après une mise à jour, et vous diagnostiquez un
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

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026.

## 📚 Exercice 1 : créer un Deployment et voir son ReplicaSet

Créez le namespace d'essai, puis écrivez le fichier d'un Deployment
`catalogue` de trois Pods :

```bash
kubectl create namespace essai-rs
cat > ~/catalogue.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: catalogue
  namespace: essai-rs
spec:
  replicas: 3
  selector:
    matchLabels:
      app: catalogue
  template:
    metadata:
      labels:
        app: catalogue
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
EOF
```

Créez-le, attendez qu'il soit prêt, puis regardez les ReplicaSets :

```bash
kubectl apply -f ~/catalogue.yaml
kubectl rollout status deployment/catalogue -n essai-rs --timeout=120s
kubectl get replicaset -n essai-rs -l app=catalogue
```

```text
deployment.apps/catalogue created
Waiting for deployment "catalogue" rollout to finish: 0 out of 3 new replicas have been updated...
Waiting for deployment "catalogue" rollout to finish: 0 of 3 updated replicas are available...
Waiting for deployment "catalogue" rollout to finish: 1 of 3 updated replicas are available...
Waiting for deployment "catalogue" rollout to finish: 2 of 3 updated replicas are available...
deployment "catalogue" successfully rolled out
NAME                  DESIRED   CURRENT   READY   AGE
catalogue-75867bdb5   3         3         3       1s
```

Un ReplicaSet est apparu. Son nom est celui du Deployment, suivi d'une
**empreinte** (`75867bdb5`) calculée à partir de la description des Pods.
`DESIRED`, `CURRENT` et `READY` disent combien de Pods il veut, en a, et en a
de prêts.

## 📚 Exercice 2 : remonter de propriétaire en propriétaire

Le champ `ownerReferences` d'un objet dit qui l'a créé. Lisez-le sur le
ReplicaSet, puis sur un Pod :

```bash
kubectl get replicaset -n essai-rs -l app=catalogue \
  -o jsonpath='{.items[0].metadata.ownerReferences[0].kind}/{.items[0].metadata.ownerReferences[0].name}{"\n"}'
kubectl get pods -n essai-rs -l app=catalogue \
  -o jsonpath='{.items[0].metadata.ownerReferences[0].kind}/{.items[0].metadata.ownerReferences[0].name}{"\n"}'
```

```text
Deployment/catalogue
ReplicaSet/catalogue-75867bdb5
```

La chaîne est complète : le Deployment possède le ReplicaSet, qui possède les
Pods. Kubernetes s'en sert pour supprimer les enfants quand on supprime le
parent.

## 📚 Exercice 3 : mettre à jour et voir un second ReplicaSet

Changez l'image du Deployment pour la version suivante de nginx :

```bash
kubectl set image deployment/catalogue \
  nginx=nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703 \
  -n essai-rs
kubectl rollout status deployment/catalogue -n essai-rs --timeout=120s | tail -1
```

```text
deployment.apps/catalogue image updated
deployment "catalogue" successfully rolled out
```

Regardez maintenant les ReplicaSets, avec les colonnes utiles :

```bash
kubectl get replicaset -n essai-rs -l app=catalogue \
  -o custom-columns=NOM:.metadata.name,VOULUS:.spec.replicas,PRETS:.status.readyReplicas,IMAGE:.spec.template.spec.containers[0].image
```

```text
NOM                    VOULUS   PRETS    IMAGE
catalogue-5f44879b68   3        3        nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
catalogue-75867bdb5    0        <none>   nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

Il y en a maintenant deux. Le nouveau porte les trois Pods, avec la nouvelle
image. L'ancien est gardé, mais à **zéro** Pod : il sert à revenir en arrière
sans rien recréer. Pour savoir lequel porte les Pods aujourd'hui, regardez la
colonne `VOULUS`.

Chaque ReplicaSet reconnaît ses Pods grâce à une étiquette qui contient son
empreinte :

```bash
kubectl get replicaset -n essai-rs -l app=catalogue \
  -o custom-columns=NOM:.metadata.name,SELECTEUR:.spec.selector.matchLabels
```

```text
NOM                    SELECTEUR
catalogue-5f44879b68   map[app:catalogue pod-template-hash:5f44879b68]
catalogue-75867bdb5    map[app:catalogue pod-template-hash:75867bdb5]
```

L'étiquette `pod-template-hash` est différente pour chacun : c'est elle qui
sépare les Pods des deux versions.

## 📚 Exercice 4 : voir un ReplicaSet adopter un Pod

Un ReplicaSet ne garde pas de liste de ses Pods. Il compte les Pods qui
portent ses étiquettes et qui n'ont pas déjà de propriétaire. Créez d'abord un
Pod seul, avec l'étiquette `app=isole` :

```bash
kubectl run isole --labels=app=isole \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-rs
kubectl wait --for=condition=Ready pod/isole -n essai-rs --timeout=90s
```

```text
pod/isole created
pod/isole condition met
```

Créez ensuite un ReplicaSet qui demande trois Pods avec cette même étiquette :

```bash
cat > ~/isole-rs.yaml <<'EOF'
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: isole-rs
  namespace: essai-rs
spec:
  replicas: 3
  selector:
    matchLabels:
      app: isole
  template:
    metadata:
      labels:
        app: isole
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
EOF
kubectl apply -f ~/isole-rs.yaml
kubectl wait --for=jsonpath='{.status.readyReplicas}'=3 replicaset/isole-rs -n essai-rs --timeout=90s
kubectl get pods -n essai-rs -l app=isole
```

```text
replicaset.apps/isole-rs created
replicaset.apps/isole-rs condition met
NAME             READY   STATUS    RESTARTS   AGE
isole            1/1     Running   0          1s
isole-rs-49gdz   1/1     Running   0          0s
isole-rs-4rhvs   1/1     Running   0          0s
```

Trois Pods, mais le ReplicaSet n'en a créé que deux. Ses événements et le
propriétaire du Pod `isole` le confirment :

```bash
kubectl describe replicaset isole-rs -n essai-rs | sed -n '/^Events:/,$p'
kubectl get pod isole -n essai-rs \
  -o jsonpath='{.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}{"\n"}'
```

```text
Events:
  Type    Reason            Age   From                   Message
  ----    ------            ----  ----                   -------
  Normal  SuccessfulCreate  0s    replicaset-controller  Created pod: isole-rs-49gdz
  Normal  SuccessfulCreate  0s    replicaset-controller  Created pod: isole-rs-4rhvs
ReplicaSet/isole-rs
```

Le Pod `isole` existait déjà et portait la bonne étiquette : le ReplicaSet l'a
pris en charge, et il est maintenant son propriétaire. À retenir : deux
contrôleurs ne doivent jamais chercher les mêmes étiquettes.

## 📚 Exercice 5 : diagnostiquer un ReplicaSet bloqué

Un **quota** limite ce qu'un namespace a le droit de contenir. Créez un
namespace limité à un seul Pod, puis un Deployment qui en demande deux :

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

`FailedCreate` donne la cause : le quota `plafond` est atteint (`used: pods=1,
limited: pods=1`). Le ReplicaSet a réessayé plusieurs fois, et la liste
complète compte une dizaine de lignes identiques.

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

Supprimez les deux namespaces d'essai et les deux fichiers :

```bash
kubectl delete namespace essai-rs essai-quota
rm ~/catalogue.yaml ~/isole-rs.yaml
```

```text
namespace "essai-rs" deleted
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
