# Un sidecar natif qui suit les logs de l'application

Un **sidecar** est un conteneur d'appoint, placé dans le même Pod qu'une
application pour l'aider : lire ses fichiers, relayer son trafic, envoyer ses
journaux ailleurs. Kubernetes propose une façon précise de le déclarer, le
**sidecar natif**. Dans ce cours, vous voyez une application que `kubectl logs`
ne montre pas, vous lui ajoutez un lecteur sous forme de second conteneur, puis
sous forme de sidecar natif, et vous voyez sur un Job ce qui les distingue.

Vous travaillez dans un namespace d'essai, `essai-sidecar`, avec un compteur
qui écrit dans un fichier et un lecteur qui le relaie. Le challenge vous
demandera la même chose sur une autre application, dans un autre namespace :
vous le ferez seul, à la fin.

Page associée : [Init containers et sidecars](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/init-containers-sidecars/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-multi-container-sidecar
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : une application qui écrit dans un fichier

Créez le namespace d'essai et un Pod `compteur-seul`. Son conteneur écrit une
ligne toutes les 2 secondes dans `/donnees/journal.txt`, sur un volume
`emptyDir` (un répertoire vide, créé avec le Pod) :

```bash
kubectl create namespace essai-sidecar
cat <<'YAML' | kubectl apply -n essai-sidecar -f -
apiVersion: v1
kind: Pod
metadata:
  name: compteur-seul
spec:
  containers:
    - name: compteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "i=0; while true; do i=$((i+1)); echo passage $i >> /donnees/journal.txt; sleep 2; done"]
      volumeMounts:
        - name: donnees
          mountPath: /donnees
  volumes:
    - name: donnees
      emptyDir: {}
YAML
```

```text
namespace/essai-sidecar created
pod/compteur-seul created
```

Attendez qu'il tourne, puis lisez ses logs (`echo` marque la fin de la
sortie) :

```bash
kubectl wait --for=condition=Ready pod/compteur-seul -n essai-sidecar --timeout=120s; sleep 6; kubectl logs compteur-seul -n essai-sidecar; echo '(fin des logs)'
```

```text
pod/compteur-seul condition met
(fin des logs)
```

Rien. `kubectl logs` ne montre que ce qu'un conteneur écrit sur sa **sortie
standard**. Ce compteur écrit dans un fichier, qui se remplit bien :

```bash
kubectl exec compteur-seul -n essai-sidecar -- tail -3 /donnees/journal.txt
```

```text
passage 2
passage 3
passage 4
```

## 📚 Exercice 2 : un second conteneur qui lit le fichier

Ajoutez au Pod un second conteneur, `lecteur`, qui suit le fichier avec
`tail -F` et le recopie sur sa propre sortie standard. Deux conteneurs d'un
même Pod ne partagent aucun fichier par défaut : le volume `donnees` est donc
monté dans les deux. Le chemin peut différer : `/donnees` pour le compteur,
`/lecture` pour le lecteur. `touch` crée le fichier s'il n'existe pas encore :

```bash
cat <<'YAML' | kubectl apply -n essai-sidecar -f -
apiVersion: v1
kind: Pod
metadata:
  name: compteur-classique
spec:
  containers:
    - name: compteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "i=0; while true; do i=$((i+1)); echo passage $i >> /donnees/journal.txt; sleep 2; done"]
      volumeMounts:
        - name: donnees
          mountPath: /donnees
    - name: lecteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "touch /lecture/journal.txt; tail -n +1 -F /lecture/journal.txt"]
      volumeMounts:
        - name: donnees
          mountPath: /lecture
  volumes:
    - name: donnees
      emptyDir: {}
YAML
```

```text
pod/compteur-classique created
```

`-c lecteur` choisit le conteneur dont on lit les logs :

```bash
kubectl wait --for=condition=Ready pod/compteur-classique -n essai-sidecar --timeout=120s; sleep 6; kubectl get pod compteur-classique -n essai-sidecar; kubectl logs compteur-classique -n essai-sidecar -c lecteur | tail -3
```

```text
pod/compteur-classique condition met
NAME                 READY   STATUS    RESTARTS   AGE
compteur-classique   2/2     Running   0          7s
passage 2
passage 3
passage 4
```

Les lignes du compteur apparaissent dans les logs du lecteur. Pour un Pod qui
tourne sans fin, cette forme suffit. L'exercice 4 montre où elle coince.

## 📚 Exercice 3 : le même lecteur en sidecar natif

Un **sidecar natif** se déclare sous `initContainers`, avec
`restartPolicy: Always`. Sans cette ligne, ce serait un init container
ordinaire, qui doit se terminer avant que l'application démarre. Avec elle,
Kubernetes le démarre avant l'application et le laisse tourner à côté :

```bash
cat <<'YAML' | kubectl apply -n essai-sidecar -f -
apiVersion: v1
kind: Pod
metadata:
  name: compteur-natif
spec:
  initContainers:
    - name: lecteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      restartPolicy: Always
      command: ["sh", "-c", "touch /lecture/journal.txt; tail -n +1 -F /lecture/journal.txt"]
      volumeMounts:
        - name: donnees
          mountPath: /lecture
  containers:
    - name: compteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "i=0; while true; do i=$((i+1)); echo passage $i >> /donnees/journal.txt; sleep 2; done"]
      volumeMounts:
        - name: donnees
          mountPath: /donnees
  volumes:
    - name: donnees
      emptyDir: {}
YAML
```

```text
pod/compteur-natif created
```

```bash
kubectl wait --for=condition=Ready pod/compteur-natif -n essai-sidecar --timeout=120s; sleep 6; kubectl get pod compteur-natif -n essai-sidecar; kubectl logs compteur-natif -n essai-sidecar -c lecteur | tail -3
```

```text
pod/compteur-natif condition met
NAME             READY   STATUS    RESTARTS   AGE
compteur-natif   2/2     Running   0          7s
passage 1
passage 2
passage 3
```

Même résultat, `2/2` compris : un sidecar natif compte parmi les conteneurs
prêts. Vérifiez où chacun est déclaré :

```bash
kubectl get pod compteur-natif -n essai-sidecar -o jsonpath='init : {.spec.initContainers[0].name} restartPolicy={.spec.initContainers[0].restartPolicy}{"\n"}principal : {.spec.containers[0].name}{"\n"}'
```

```text
init : lecteur restartPolicy=Always
principal : compteur
```

## 📚 Exercice 4 : un Job avec un sidecar classique

La différence se voit sur un **Job**, un Pod qui fait une tâche puis
s'arrête. Lancez un Job `rapport-classique` : son conteneur `rapport` écrit
trois lignes en 3 secondes puis se termine, et le lecteur est un second
conteneur ordinaire, comme à l'exercice 2 :

```bash
cat <<'YAML' | kubectl apply -n essai-sidecar -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: rapport-classique
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: rapport
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "for i in 1 2 3; do echo ligne $i >> /donnees/journal.txt; sleep 1; done; echo rapport termine"]
          volumeMounts:
            - name: donnees
              mountPath: /donnees
        - name: lecteur
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "touch /lecture/journal.txt; tail -n +1 -F /lecture/journal.txt"]
          volumeMounts:
            - name: donnees
              mountPath: /lecture
      volumes:
        - name: donnees
          emptyDir: {}
YAML
```

```text
job.batch/rapport-classique created
```

25 secondes plus tard :

```bash
sleep 25; kubectl get job rapport-classique -n essai-sidecar; kubectl get pods -n essai-sidecar -l job-name=rapport-classique
```

```text
NAME                STATUS    COMPLETIONS   DURATION   AGE
rapport-classique   Running   0/1           25s        25s
NAME                      READY   STATUS     RESTARTS   AGE
rapport-classique-mf8br   1/2     NotReady   0          25s
```

Le rapport a fini depuis longtemps, mais le Job tourne toujours (`0/1`) : le
lecteur, lui, ne s'arrête jamais. Un Job n'est terminé que lorsque **tous**
ses conteneurs ordinaires le sont. Ce Job ne finira jamais.

## 📚 Exercice 5 : le même Job avec un sidecar natif

Même Job, mais le lecteur devient un sidecar natif :

```bash
cat <<'YAML' | kubectl apply -n essai-sidecar -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: rapport-natif
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      initContainers:
        - name: lecteur
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          restartPolicy: Always
          command: ["sh", "-c", "touch /lecture/journal.txt; tail -n +1 -F /lecture/journal.txt"]
          volumeMounts:
            - name: donnees
              mountPath: /lecture
      containers:
        - name: rapport
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "for i in 1 2 3; do echo ligne $i >> /donnees/journal.txt; sleep 1; done; echo rapport termine"]
          volumeMounts:
            - name: donnees
              mountPath: /donnees
      volumes:
        - name: donnees
          emptyDir: {}
YAML
```

```text
job.batch/rapport-natif created
```

```bash
kubectl wait --for=condition=complete job/rapport-natif -n essai-sidecar --timeout=120s; kubectl get job rapport-natif -n essai-sidecar; kubectl get pods -n essai-sidecar -l job-name=rapport-natif
kubectl logs job/rapport-natif -n essai-sidecar -c lecteur
```

```text
job.batch/rapport-natif condition met
NAME            STATUS     COMPLETIONS   DURATION   AGE
rapport-natif   Complete   1/1           37s        37s
NAME                  READY   STATUS      RESTARTS   AGE
rapport-natif-drwr6   0/2     Completed   0          37s
ligne 1
ligne 2
ligne 3
```

Le Job se termine (`Complete`) et le lecteur a bien relayé les trois lignes.
Quand le conteneur principal a fini, Kubernetes arrête lui-même le sidecar
natif. Mais pourquoi 37 secondes pour 3 secondes de travail ? Regardez comment
chaque conteneur s'est arrêté :

```bash
kubectl get pods -n essai-sidecar -l job-name=rapport-natif -o jsonpath='{range .items[0].status.initContainerStatuses[*]}{.name} {.state.terminated.reason} {.state.terminated.exitCode}{"\n"}{end}{range .items[0].status.containerStatuses[*]}{.name} {.state.terminated.reason} {.state.terminated.exitCode}{"\n"}{end}'
```

```text
lecteur Error 137
rapport Completed 0
```

Le rapport s'est terminé normalement (code 0). Le lecteur a le code 137 : il a
été **tué de force**. Kubernetes lui a d'abord demandé de s'arrêter, mais
`tail`, lancé par `sh -c`, n'a pas réagi. Kubernetes a donc attendu le délai
prévu, 30 secondes par défaut, avant de le tuer. Un sidecar qui s'arrête
proprement quand on le lui demande ne fait pas attendre son Job.

## 🧹 Nettoyage

Supprimez le namespace d'essai, avec ses Pods et ses Jobs :

```bash
kubectl delete namespace essai-sidecar
```

```text
namespace "essai-sidecar" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-multi-container-sidecar
dsoxlab check ckad-multi-container-sidecar
```

```text
╭─ Résultat : ckad-multi-container-sidecar ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests          │
╰───────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une autre application qui écrit ses logs dans un
fichier, et un sidecar natif qui les relaie.

```bash
dsoxlab run ckad-multi-container-sidecar
dsoxlab challenge ckad-multi-container-sidecar
```
