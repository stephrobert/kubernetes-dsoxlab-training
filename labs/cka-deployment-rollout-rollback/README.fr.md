# Revenir en arrière sur un déploiement bloqué

Un Deployment garde l'historique de ses versions. Chaque changement du modèle
de ses Pods crée une **révision** numérotée, et l'ancienne version reste en
réserve, à zéro Pod. La leçon livre une image fausse, revient en arrière, puis
livre la bonne image. Ce cours prend une autre panne : une livraison bloquée
alors que l'image est bonne. Vous la diagnostiquez par les conditions du
Deployment, vous revenez en arrière, puis vous voyez pourquoi changer l'image
ne répare pas une panne qui n'est pas dans l'image.

Vous travaillez dans un namespace d'essai, `essai-livraison`, avec un
Deployment `affiche`. Le challenge vous demandera de réparer un autre
Deployment, déjà bloqué : vous le ferez seul, à la fin.

Page associée : [Deployments Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/deployments/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-deployment-rollout-rollback
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : livrer une première version

Écrivez le Deployment `affiche` dans un fichier. Il porte une **sonde de
disponibilité** (readinessProbe) : le kubelet interroge le port 80 toutes les
deux secondes, et le Pod ne reçoit du trafic que si nginx répond.
`progressDeadlineSeconds: 30` dit au Deployment de signaler une livraison
qui n'avance plus au bout de 30 secondes.

```bash
kubectl create namespace essai-livraison
cat > ~/essai-affiche.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: affiche
  namespace: essai-livraison
spec:
  replicas: 3
  progressDeadlineSeconds: 30
  selector:
    matchLabels:
      app: affiche
  template:
    metadata:
      labels:
        app: affiche
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          readinessProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 2
EOF
kubectl apply -f ~/essai-affiche.yaml
kubectl rollout status deployment/affiche -n essai-livraison --timeout=120s
kubectl rollout history deployment/affiche -n essai-livraison
```

```text title="Extrait de la sortie"
namespace/essai-livraison created
deployment.apps/affiche created
deployment "affiche" successfully rolled out
deployment.apps/affiche
REVISION  CHANGE-CAUSE
1         <none>
```

Une révision, la 1.

## 📚 Exercice 2 : diagnostiquer une livraison qui bloque

Un collègue modifie la sonde et vise le port 8080, où nginx n'écoute pas.
Faites la même erreur, puis appliquez :

```bash
sed -i 's/port: 80/port: 8080/' ~/essai-affiche.yaml
kubectl apply -f ~/essai-affiche.yaml
kubectl rollout status deployment/affiche -n essai-livraison --timeout=45s
```

```text
deployment.apps/affiche configured
Waiting for deployment "affiche" rollout to finish: 1 out of 3 new replicas have been updated...
error: deployment "affiche" exceeded its progress deadline
```

`rollout status` abandonne et sort en erreur. Regardez les Pods :

```bash
kubectl get pods -n essai-livraison
```

```text
NAME                       READY   STATUS    RESTARTS   AGE
affiche-576cfff896-wszxz   0/1     Running   0          31s
affiche-5b56f6c8d-9rnfc    1/1     Running   0          33s
affiche-5b56f6c8d-qjzp6    1/1     Running   0          33s
affiche-5b56f6c8d-vt674    1/1     Running   0          33s
```

Le nouveau Pod tourne (`Running`) sans aucun redémarrage, mais il n'est pas
prêt (`0/1`). Rien ne plante, et pourtant la livraison est arrêtée : le
Deployment attend qu'un nouveau Pod soit prêt avant de retirer un ancien. Les
trois anciens Pods tiennent toujours le service. Les **conditions** du
Deployment le résument :

```bash
kubectl describe deployment affiche -n essai-livraison | sed -n '/^Conditions:/,/^OldReplicaSets/p'
```

```text
Conditions:
  Type           Status  Reason
  ----           ------  ------
  Available      True    MinimumReplicasAvailable
  Progressing    False   ProgressDeadlineExceeded
OldReplicaSets:  affiche-5b56f6c8d (3/3 replicas created)
```

`Available True` : le service tourne. `Progressing False` avec
`ProgressDeadlineExceeded` : la livraison n'a pas avancé en 30 secondes. La
raison se lit dans les événements du Pod qui n'est pas prêt :

```bash
POD=$(kubectl get pods -n essai-livraison -o jsonpath='{range .items[?(@.status.containerStatuses[0].ready==false)]}{.metadata.name}{end}')
kubectl describe pod $POD -n essai-livraison | grep -E 'Readiness|Unhealthy'
```

```text
    Readiness:      http-get http://:8080/ delay=0s timeout=1s period=2s successThreshold=1 failureThreshold=3
  Warning  Unhealthy  2s (x16 over 31s)  kubelet            spec.containers{nginx}: Readiness probe failed: Get "http://10.244.38.81:8080/": dial tcp 10.244.38.81:8080: connect: connection refused
```

La sonde vise le port 8080, et rien n'y répond.

## 📚 Exercice 3 : revenir en arrière, et voir ce qui tourne

Avant de revenir en arrière, notez les deux ReplicaSets :

```bash
kubectl get rs -n essai-livraison
```

```text
NAME                 DESIRED   CURRENT   READY   AGE
affiche-576cfff896   1         1         0       31s
affiche-5b56f6c8d    3         3         3       33s
```

Revenez à la révision précédente, et attendez la fin :

```bash
kubectl rollout undo deployment/affiche -n essai-livraison
kubectl rollout status deployment/affiche -n essai-livraison --timeout=120s
```

```text
Warning: resource deployments/affiche was previously managed with 'kubectl apply'. Rolling back will not update the kubectl.kubernetes.io/last-applied-configuration annotation, which may cause unexpected behavior on future 'kubectl apply' operations. Consider using 'kubectl apply' with your previous configuration file instead.
deployment.apps/affiche rolled back
Waiting for deployment "affiche" rollout to finish: 1 old replicas are pending termination...
deployment "affiche" successfully rolled out
```

Gardez cet avertissement en tête : vous en verrez l'effet à l'exercice 5.
Regardez maintenant les ReplicaSets et l'historique :

```bash
kubectl get rs -n essai-livraison
kubectl rollout history deployment/affiche -n essai-livraison
```

```text
NAME                 DESIRED   CURRENT   READY   AGE
affiche-576cfff896   0         0         0       31s
affiche-5b56f6c8d    3         3         3       33s
deployment.apps/affiche
REVISION  CHANGE-CAUSE
2         <none>
3         <none>
```

Aucun ReplicaSet neuf : `affiche-5b56f6c8d`, celui de la révision 1, a repris
le service et porte maintenant le numéro 3. Vérifiez ce que les Pods font
tourner :

```bash
kubectl get pods -n essai-livraison -o jsonpath='{range .items[*]}{.metadata.name}{"  "}{.spec.containers[0].image}{"\n"}{end}'
```

```text
affiche-576cfff896-wszxz  nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
affiche-5b56f6c8d-9rnfc  nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
affiche-5b56f6c8d-qjzp6  nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
affiche-5b56f6c8d-vt674  nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

Les deux révisions avaient la même image : seule la sonde différait. Le Pod
`wszxz` de la révision fautive est encore listé : il est en cours d'arrêt.

## 📚 Exercice 4 : livrer l'image suivante et écrire sa cause

Livrez `nginx:1.30.6`, puis écrivez la raison du changement dans
l'annotation `kubernetes.io/change-cause`. Corrigez ensuite ce texte :

```bash
kubectl set image deployment/affiche nginx=nginx:1.30.6 -n essai-livraison
kubectl rollout status deployment/affiche -n essai-livraison --timeout=120s
kubectl annotate deployment/affiche -n essai-livraison kubernetes.io/change-cause='passage à nginx 1.30.6'
kubectl annotate deployment/affiche -n essai-livraison kubernetes.io/change-cause='nginx 1.30.6, sonde sur le port 80'
kubectl rollout history deployment/affiche -n essai-livraison
```

```text title="Extrait de la sortie"
deployment.apps/affiche image updated
deployment "affiche" successfully rolled out
deployment.apps/affiche annotated
deployment.apps/affiche annotated
deployment.apps/affiche
REVISION  CHANGE-CAUSE
2         <none>
3         <none>
4         nginx 1.30.6, sonde sur le port 80
```

Le second `annotate` a remplacé le premier texte sans erreur. Pour cette clé,
`kubernetes.io/change-cause`, kubectl v1.37.2 remplace l'ancienne valeur
directement. Pour toute autre annotation, il refuse sans l'option
`--overwrite`, avec le message
`--overwrite is false but found the following declared annotation(s)`. Ajouter
`--overwrite` marche dans les deux cas.

## 📚 Exercice 5 : changer l'image ne répare pas une sonde fausse

Votre fichier `~/essai-affiche.yaml` contient toujours la sonde sur le port
8080 : le retour en arrière a changé le cluster, pas le fichier. Appliquez-le
de nouveau, comme le ferait un collègue qui reprend son travail, puis
regardez les Pods une trentaine de secondes plus tard :

```bash
kubectl apply -f ~/essai-affiche.yaml
kubectl get pods -n essai-livraison
```

```text
deployment.apps/affiche configured
NAME                       READY   STATUS    RESTARTS   AGE
affiche-576cfff896-6tc58   0/1     Running   0          35s
affiche-5fd8fdd64b-4d94t   1/1     Running   0          39s
affiche-5fd8fdd64b-csgw6   1/1     Running   0          37s
affiche-5fd8fdd64b-lwnss   1/1     Running   0          41s
```

La panne est revenue. Le ReplicaSet `affiche-576cfff896` reprend même du
service : le fichier décrit exactement la révision fautive. Essayez de réparer
en changeant l'image :

```bash
kubectl set image deployment/affiche nginx=nginx:1.30.5 -n essai-livraison
kubectl rollout status deployment/affiche -n essai-livraison --timeout=45s
kubectl get deployment affiche -n essai-livraison -o jsonpath='{.spec.template.spec.containers[0].image} {.spec.template.spec.containers[0].readinessProbe.httpGet.port}{"\n"}'
```

```text title="Extrait de la sortie"
deployment.apps/affiche image updated
error: deployment "affiche" exceeded its progress deadline
nginx:1.30.5 8080
```

Nouvelle image, même blocage : `set image` ne change que l'image, et la sonde
vise toujours le port 8080. Regardez ce qu'est devenu l'historique :

```bash
kubectl rollout history deployment/affiche -n essai-livraison
```

```text
deployment.apps/affiche
REVISION  CHANGE-CAUSE
3         <none>
4         nginx 1.30.6, sonde sur le port 80
5         nginx 1.30.6, sonde sur le port 80
6         nginx 1.30.6, sonde sur le port 80
```

Deux révisions de plus, et la cause de la révision 4 recopiée sur la 5 et la
6, où elle est fausse : l'annotation reste sur le Deployment, et chaque
nouvelle révision la reprend. Avant de livrer, cherchez donc ce qui bloque :
ici `Unhealthy` dans les événements du Pod, pas l'image.

## 🧹 Nettoyage

Supprimez d'abord ce que vous avez créé pendant les exercices : le namespace
d'essai et le fichier du Deployment.

```bash
kubectl delete namespace essai-livraison
rm ~/essai-affiche.yaml
```

```text
namespace "essai-livraison" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-deployment-rollout-rollback
dsoxlab check cka-deployment-rollout-rollback
```

```text
╭─ Résultat : cka-deployment-rollout-rollback ─╮
│  0 / 100 pts                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/8 tests             │
╰──────────────────────────────────────────────╯
```

0 sur 8 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un Deployment est bloqué sur une image qui s'arrête
en boucle. Revenez à la version qui marchait, puis livrez la bonne image, avec sa
cause.

```bash
dsoxlab run cka-deployment-rollout-rollback
dsoxlab challenge cka-deployment-rollout-rollback
```
