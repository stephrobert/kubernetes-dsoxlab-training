# Diagnostiquer deux Pods en échec

Un **Pod** est la plus petite chose que Kubernetes fait tourner : un ou
plusieurs conteneurs qui vivent ensemble. Dans ce cours, vous créez des Pods
de deux façons, vous apprenez à les observer, puis vous diagnostiquez les deux
pannes les plus courantes : une image introuvable et un programme qui
s'arrête en boucle.

Vous travaillez dans un namespace d'essai, `essai-pods`. Le challenge vous
demandera de diagnostiquer et de réparer deux autres Pods : vous le ferez
seul, à la fin.

Page associée : [Pods Kubernetes : créer, observer et diagnostiquer](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/pods/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-diagnostiquer-un-pod
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`boutique` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026.

## 📚 Exercice 1 : créer un Pod en une commande

Créez le namespace d'essai, puis un Pod `accueil` qui lance nginx :

```bash
kubectl create namespace essai-pods
kubectl run accueil \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-pods
kubectl wait --for=condition=Ready pod/accueil -n essai-pods --timeout=90s
kubectl get pods -n essai-pods
```

```text
namespace/essai-pods created
pod/accueil created
pod/accueil condition met
NAME      READY   STATUS    RESTARTS   AGE
accueil   1/1     Running   0          1s
```

`1/1 Running` avec `0` redémarrage : c'est l'état d'un Pod en bonne santé.
`READY` compte les conteneurs prêts, `RESTARTS` les redémarrages.

## 📚 Exercice 2 : écrire le manifeste d'un Pod

kubectl peut écrire le fichier YAML d'un Pod à votre place, sans rien créer,
grâce à `--dry-run=client -o yaml` :

```bash
kubectl run fiche \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-pods --dry-run=client -o yaml
```

```text
apiVersion: v1
kind: Pod
metadata:
  labels:
    run: fiche
  name: fiche
  namespace: essai-pods
spec:
  containers:
  - image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
    name: fiche
    resources: {}
  dnsPolicy: ClusterFirst
  restartPolicy: Always
status: {}
```

C'est un bon point de départ. Écrivez maintenant votre propre manifeste dans
`~/fiche.yaml`, puis créez le Pod à partir de lui :

```bash
cat > ~/fiche.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: fiche
  namespace: essai-pods
  labels:
    app: fiche
spec:
  restartPolicy: Always
  containers:
    - name: nginx
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      ports:
        - containerPort: 80
EOF
kubectl apply -f ~/fiche.yaml
kubectl wait --for=condition=Ready pod/fiche -n essai-pods --timeout=90s
```

```text
pod/fiche created
pod/fiche condition met
```

Un fichier comme celui-ci se garde et se partage : c'est la façon de faire
d'une équipe. La commande de l'exercice 1 sert plutôt à essayer.

## 📚 Exercice 3 : observer un Pod

Quatre commandes s'emploient toujours dans cet ordre, de la plus légère à la
plus intrusive. D'abord, où en est le Pod :

```bash
kubectl get pod accueil -n essai-pods -o wide
```

```text
NAME      READY   STATUS    RESTARTS   AGE   IP            NODE                     NOMINATED NODE   READINESS GATES
accueil   1/1     Running   0          2s    10.244.0.15   boutique-control-plane   <none>           <none>
```

`-o wide` ajoute l'adresse du Pod et le nœud où il tourne. Ensuite, ce que
Kubernetes a fait pour lui, à la fin de `describe` :

```bash
kubectl describe pod accueil -n essai-pods | sed -n '/^Events:/,$p'
```

```text
Events:
  Type    Reason     Age   From               Message
  ----    ------     ----  ----               -------
  Normal  Scheduled  2s    default-scheduler  Successfully assigned essai-pods/accueil to boutique-control-plane
  Normal  Pulled     1s    kubelet            spec.containers{accueil}: Container image "nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb" already present on machine and can be accessed by the pod
  Normal  Created    1s    kubelet            spec.containers{accueil}: Container created
  Normal  Started    1s    kubelet            spec.containers{accueil}: Container started
```

Les événements racontent les étapes dans l'ordre : placement sur un nœud,
image déjà présente, conteneur créé, puis démarré. Puis ce que l'application
a écrit, et enfin une commande lancée **dans** le conteneur :

```bash
kubectl logs accueil -n essai-pods --tail=3
kubectl exec accueil -n essai-pods -- hostname
```

```text
2026/11/19 11:38:42 [notice] 1#1: start worker processes
2026/11/19 11:38:42 [notice] 1#1: start worker process 35
2026/11/19 11:38:42 [notice] 1#1: start worker process 36
accueil
```

`kubectl exec` lance la commande `hostname` dans le conteneur, qui répond par
le nom du Pod.

## 📚 Exercice 4 : lire la phase d'un Pod

La **phase** résume en un mot où en est un Pod : `Pending` (pas encore
démarré), `Running`, `Succeeded` ou `Failed` (terminé).

```bash
kubectl get pod accueil -n essai-pods -o jsonpath='{.status.phase}{"\n"}'
```

```text
Running
```

## 📚 Exercice 5 : diagnostiquer une image introuvable

Créez un Pod qui demande une version de nginx qui n'existe pas, puis
attendez un peu :

```bash
kubectl run mauvais-tag --image=nginx:9.9.9 -n essai-pods
sleep 20
kubectl get pod mauvais-tag -n essai-pods
```

```text
pod/mauvais-tag created
NAME          READY   STATUS             RESTARTS   AGE
mauvais-tag   0/1     ImagePullBackOff   0          20s
```

`ImagePullBackOff` : Kubernetes n'arrive pas à télécharger l'image, et il
attend de plus en plus longtemps entre deux essais. La cause est dans les
avertissements de `describe` :

```bash
kubectl describe pod mauvais-tag -n essai-pods | grep -E 'Warning|Status:'
```

```text
Status:           Pending
  Warning  Failed     19s               kubelet            spec.containers{mauvais-tag}: Error: ImagePullBackOff
  Warning  Failed     6s (x2 over 19s)  kubelet            spec.containers{mauvais-tag}: Failed to pull image "nginx:9.9.9": rpc error: code = NotFound desc = failed to pull and unpack image "docker.io/library/nginx:9.9.9": failed to resolve reference "docker.io/library/nginx:9.9.9": docker.io/library/nginx:9.9.9: not found
  Warning  Failed     6s (x2 over 19s)  kubelet            spec.containers{mauvais-tag}: Error: ErrImagePull
```

`nginx:9.9.9: not found` : cette version n'existe pas. Le Pod reste en phase
`Pending`, puisque son conteneur n'a jamais démarré.

## 📚 Exercice 6 : diagnostiquer un conteneur qui plante

Créez un Pod dont le programme s'arrête tout de suite avec le code `2` :

```bash
kubectl run chute \
  --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 \
  -n essai-pods -- sh -c 'echo "je tombe"; exit 2'
sleep 45
kubectl get pod chute -n essai-pods
```

```text
pod/chute created
NAME    READY   STATUS   RESTARTS      AGE
chute   0/1     Error    3 (33s ago)   45s
```

Kubernetes relance le conteneur après chaque arrêt : `RESTARTS` est déjà à 3.
Selon le moment, `STATUS` affiche `Error`, `CrashLoopBackOff` ou `Running`.
Le code de sortie du dernier arrêt est rangé dans l'état du Pod :

```bash
kubectl get pod chute -n essai-pods -o jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}{"\n"}'
kubectl get pod chute -n essai-pods -o jsonpath='{.status.phase}{"\n"}'
```

```text
2
Running
```

Le code `2` est bien celui du programme. Remarquez que la phase reste
`Running`, alors que le conteneur plante en boucle : la phase seule ne suffit
pas pour juger un Pod. Regardez aussi `STATUS` et `RESTARTS`.

## 📚 Exercice 7 : voir l'effet de `restartPolicy`

`restartPolicy` dit à Kubernetes quoi faire quand un conteneur s'arrête. Par
défaut (`Always`), il le relance toujours. Avec `Never`, il ne le relance
jamais. Créez deux Pods qui ne sont jamais relancés, l'un qui réussit et
l'autre qui échoue :

```bash
kubectl run reussit --restart=Never \
  --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 \
  -n essai-pods -- sh -c 'echo ok; exit 0'
kubectl run echoue --restart=Never \
  --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 \
  -n essai-pods -- sh -c 'echo ko; exit 1'
sleep 15
kubectl get pods reussit echoue -n essai-pods
```

```text
pod/reussit created
pod/echoue created
NAME      READY   STATUS      RESTARTS   AGE
reussit   0/1     Completed   0          15s
echoue    0/1     Error       0          15s
```

`reussit` est `Completed` (code 0) et `echoue` est `Error` (code 1). Aucun des
deux n'a été relancé : `RESTARTS` reste à 0.

## 📚 Exercice 8 : voir qu'un Pod seul n'est pas recréé

Un Pod créé directement, comme `accueil`, n'est surveillé par personne.
Supprimez-le :

```bash
kubectl delete pod accueil -n essai-pods
kubectl get pods -n essai-pods
```

```text
pod "accueil" deleted from essai-pods namespace
NAME          READY   STATUS             RESTARTS      AGE
chute         0/1     Error              3 (49s ago)   61s
echoue        0/1     Error              0             16s
fiche         1/1     Running            0             82s
mauvais-tag   0/1     ImagePullBackOff   0             81s
reussit       0/1     Completed          0             16s
```

`accueil` ne revient pas : aucun contrôleur n'a été chargé d'en garder un. En
pratique, on fait gérer ses Pods par un Deployment, qui les recrée.

## 🧹 Nettoyage

Supprimez le namespace d'essai, avec tous ses Pods, et le fichier du manifeste :

```bash
kubectl delete namespace essai-pods
rm ~/fiche.yaml
```

```text
namespace "essai-pods" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-diagnostiquer-un-pod
dsoxlab check k8s-diagnostiquer-un-pod
```

```text
╭─ Résultat : k8s-diagnostiquer-un-pod ─╮
│  0 / 100 pts                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests      │
╰───────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : diagnostiquer les deux Pods en panne du namespace
`pods-en-panne`, puis les réparer, chacun de la bonne façon.

```bash
dsoxlab run k8s-diagnostiquer-un-pod
dsoxlab challenge k8s-diagnostiquer-un-pod
```
