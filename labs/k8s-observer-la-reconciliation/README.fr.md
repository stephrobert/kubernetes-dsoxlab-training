# Observer la réconciliation du control plane

Le **control plane** est la partie du cluster qui décide : il garde l'état que
vous avez demandé et fait en sorte que le cluster s'y conforme. Ses
composants tournent sous forme de Pods sur le nœud `control-plane` :

- l'**API server** reçoit toutes les demandes ;
- **etcd** est la base de données qui garde l'état du cluster ;
- le **scheduler** choisit un nœud pour chaque Pod ;
- le **controller manager** fait tourner les **contrôleurs**.

Un contrôleur compare sans arrêt ce que vous avez demandé à ce qui existe, et
corrige l'écart. On appelle ça la **réconciliation**. Dans ce cours, vous
provoquez des écarts et vous regardez les contrôleurs les corriger.

Vous travaillez dans un namespace d'essai, `essai-boucle`, avec un Deployment
`boucle`. Le challenge vous demandera de refaire l'observation sur une autre
application : vous le ferez seul, à la fin.

Page associée : [Control Plane Kubernetes : API Server, etcd, Scheduler](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/control-plan/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-observer-la-reconciliation
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`architecture` y tourne, avec un control plane et trois workers, et votre
kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026.

## 📚 Exercice 1 : trouver les composants du control plane

Sur kind, les composants du control plane sont des Pods du namespace
`kube-system`, avec l'étiquette `tier=control-plane` :

```bash
kubectl get pods -n kube-system -l tier=control-plane
```

```text
NAME                                                 READY   STATUS    RESTARTS   AGE
etcd-architecture-control-plane                      1/1     Running   0          5m53s
kube-apiserver-architecture-control-plane            1/1     Running   0          5m53s
kube-controller-manager-architecture-control-plane   1/1     Running   0          5m53s
kube-scheduler-architecture-control-plane            1/1     Running   0          5m53s
```

Les quatre composants tournent. Ce sont des Pods particuliers : le kubelet du
nœud les lance lui-même, à partir de fichiers posés sur le nœud, sans passer
par le scheduler. Vérifiez-le sur celui du scheduler :

```bash
kubectl describe pod -n kube-system kube-scheduler-architecture-control-plane \
  | grep -E 'config.source|Controlled By'
```

```text
                      kubernetes.io/config.source: file
Controlled By:  Node/architecture-control-plane
```

`config.source: file` : le Pod vient d'un fichier du nœud. `Controlled By`
désigne le nœud, et non un ReplicaSet.

## 📚 Exercice 2 : demander à l'API server s'il va bien

```bash
kubectl get --raw /readyz; echo
kubectl get --raw '/readyz?verbose' | grep -E 'etcd |passed'
```

```text
ok
[+]etcd ok
readyz check passed
```

`ok` : l'API server est prêt à répondre. Avec `?verbose`, il détaille ses
vérifications, dont celle d'etcd : `[+]etcd ok` montre qu'il joint bien la
base de données.

## 📚 Exercice 3 : créer un Pod qu'aucun nœud n'accepte

Le scheduler ne lance aucun conteneur : il choisit seulement un nœud.
Vérifiez-le avec un Pod qui exige une étiquette `disque: ssd`, qu'aucun nœud
ne porte. Créez le namespace d'essai, puis le fichier du Pod :

```bash
kubectl create namespace essai-boucle
cat > ~/exige-ssd.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: exige-ssd
  namespace: essai-boucle
spec:
  nodeSelector:
    disque: ssd
  containers:
    - name: web
      image: nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
EOF
```

Créez le Pod, attendez quelques secondes, puis regardez-le :

```bash
kubectl apply -f ~/exige-ssd.yaml
sleep 5
kubectl get pod exige-ssd -n essai-boucle
kubectl describe pod exige-ssd -n essai-boucle | sed -n '/^Events:/,$p'
```

```text
pod/exige-ssd created
NAME        READY   STATUS    RESTARTS   AGE
exige-ssd   0/1     Pending   0          5s
Events:
  Type     Reason            Age   From               Message
  ----     ------            ----  ----               -------
  Warning  FailedScheduling  5s    default-scheduler  0/4 nodes are available: 1 node(s) had untolerated taint(s), 3 node(s) didn't match Pod's node affinity/selector. preemption: 0/4 nodes are available: 4 Preemption is not helpful for scheduling.
```

Le Pod reste `Pending` : le scheduler n'a trouvé aucun nœud, donc aucun
conteneur n'a démarré. Le message dit pourquoi, nœud par nœud : le control
plane est écarté par sa marque (`taint`), les trois workers parce qu'ils n'ont
pas l'étiquette `disque: ssd`. Devant un Pod `Pending`, lisez d'abord ces
événements. Supprimez ensuite ce Pod d'essai :

```bash
kubectl delete pod exige-ssd -n essai-boucle
rm ~/exige-ssd.yaml
```

```text
pod "exige-ssd" deleted from essai-boucle namespace
```

## 📚 Exercice 4 : changer le nombre de Pods demandé

Créez un Deployment de trois Pods, attendez qu'il soit prêt, puis demandez-en
cinq :

```bash
kubectl create deployment boucle \
  --image=nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  --replicas=3 -n essai-boucle
kubectl wait --for=condition=Available deployment/boucle -n essai-boucle --timeout=180s
kubectl scale deployment boucle --replicas=5 -n essai-boucle
kubectl get pods -n essai-boucle
```

```text
deployment.apps/boucle created
deployment.apps/boucle condition met
deployment.apps/boucle scaled
NAME                      READY   STATUS              RESTARTS   AGE
boucle-5f64888d87-4dss7   1/1     Running             0          1s
boucle-5f64888d87-8hnwr   0/1     ContainerCreating   0          0s
boucle-5f64888d87-h2sz9   1/1     Running             0          1s
boucle-5f64888d87-kqvs7   1/1     Running             0          1s
boucle-5f64888d87-r8x4t   0/1     Pending             0          0s
```

Vous avez changé un seul nombre, et deux Pods sont apparus (âge `0s`). Revenez
à trois, puis lisez les événements du ReplicaSet :

```bash
kubectl scale deployment boucle --replicas=3 -n essai-boucle
sleep 5
RS=$(kubectl get rs -n essai-boucle -o jsonpath='{.items[0].metadata.name}')
kubectl describe rs $RS -n essai-boucle | sed -n '/^Events:/,$p'
```

```text
deployment.apps/boucle scaled
Events:
  Type    Reason            Age   From                   Message
  ----    ------            ----  ----                   -------
  Normal  SuccessfulCreate  6s    replicaset-controller  Created pod: boucle-5f64888d87-kqvs7
  Normal  SuccessfulCreate  6s    replicaset-controller  Created pod: boucle-5f64888d87-4dss7
  Normal  SuccessfulCreate  6s    replicaset-controller  Created pod: boucle-5f64888d87-h2sz9
  Normal  SuccessfulCreate  5s    replicaset-controller  Created pod: boucle-5f64888d87-8hnwr
  Normal  SuccessfulCreate  5s    replicaset-controller  Created pod: boucle-5f64888d87-r8x4t
  Normal  SuccessfulDelete  5s    replicaset-controller  Deleted pod: boucle-5f64888d87-r8x4t
  Normal  SuccessfulDelete  5s    replicaset-controller  Deleted pod: boucle-5f64888d87-8hnwr
```

Lisez dans l'ordre. Les trois premiers `SuccessfulCreate` : la création du
Deployment. Les deux suivants : le passage à cinq, le contrôleur a vu 3 Pods
pour 5 demandés et en a créé 2. Les deux `SuccessfulDelete` : le retour à
trois, il a vu 5 Pods pour 3 demandés et en a supprimé 2. Le même contrôleur,
`replicaset-controller`, a fait tout ce travail.

## 📚 Exercice 5 : supprimer le ReplicaSet et le voir revenir

La même boucle existe un niveau plus haut. Supprimez le ReplicaSet lui-même,
et regardez tout de suite ce qui existe :

```bash
RS=$(kubectl get rs -n essai-boucle -o jsonpath='{.items[0].metadata.name}')
kubectl delete rs $RS -n essai-boucle
kubectl get rs,pods -n essai-boucle
```

```text
replicaset.apps "boucle-5f64888d87" deleted from essai-boucle namespace
NAME                                DESIRED   CURRENT   READY   AGE
replicaset.apps/boucle-5f64888d87   3         3         0       0s

NAME                          READY   STATUS              RESTARTS   AGE
pod/boucle-5f64888d87-4dss7   1/1     Terminating         0          6s
pod/boucle-5f64888d87-4thmb   0/1     ContainerCreating   0          0s
pod/boucle-5f64888d87-h2sz9   1/1     Terminating         0          6s
pod/boucle-5f64888d87-kqvs7   1/1     Terminating         0          6s
pod/boucle-5f64888d87-srzb7   0/1     Pending             0          0s
pod/boucle-5f64888d87-w47sh   0/1     Pending             0          0s
```

Deux choses se passent en même temps. Les trois anciens Pods sont en
`Terminating` : ils disparaissent avec leur ReplicaSet. Mais un ReplicaSet
existe déjà de nouveau (âge `0s`), avec trois Pods neufs. Il porte le même nom,
parce que ce nom est calculé à partir de la description des Pods, qui n'a pas
changé. Quinze secondes plus tard, tout est revenu :

```bash
sleep 15
kubectl get rs,pods -n essai-boucle
```

```text
NAME                                DESIRED   CURRENT   READY   AGE
replicaset.apps/boucle-5f64888d87   3         3         3       15s

NAME                          READY   STATUS    RESTARTS   AGE
pod/boucle-5f64888d87-4thmb   1/1     Running   0          15s
pod/boucle-5f64888d87-srzb7   1/1     Running   0          15s
pod/boucle-5f64888d87-w47sh   1/1     Running   0          15s
```

Qui a recréé le ReplicaSet ? Les événements du Deployment le disent :

```bash
kubectl describe deployment boucle -n essai-boucle | sed -n '/^Events:/,$p'
```

```text
Events:
  Type    Reason             Age                From                   Message
  ----    ------             ----               ----                   -------
  Normal  ScalingReplicaSet  20s                deployment-controller  Scaled up replica set boucle-5f64888d87 from 3 to 5
  Normal  ScalingReplicaSet  20s                deployment-controller  Scaled down replica set boucle-5f64888d87 from 5 to 3
  Normal  ScalingReplicaSet  15s (x2 over 21s)  deployment-controller  Scaled up replica set boucle-5f64888d87 from 0 to 3
```

`deployment-controller` a vu qu'il manquait un ReplicaSet, et l'a recréé avec
3 Pods. `(x2 over 21s)` : il l'a déjà fait deux fois, à la création du
Deployment puis après la suppression.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-boucle
```

```text
namespace "essai-boucle" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-observer-la-reconciliation
dsoxlab check k8s-observer-la-reconciliation
```

```text
╭─ Résultat : k8s-observer-la-reconciliation ─╮
│  0 / 100 pts                                │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests            │
╰─────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : supprimer un Pod puis le ReplicaSet de l'application
du challenge, et relever quel contrôleur a recréé chacun.

```bash
dsoxlab run k8s-observer-la-reconciliation
dsoxlab challenge k8s-observer-la-reconciliation
```
