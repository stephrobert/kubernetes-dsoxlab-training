# Un Pod à deux conteneurs et ses budgets de ressources

Sur un cluster partagé, chaque conteneur déclare un **budget** : ce qu'il
**demande** (requests), que le cluster lui réserve, et ce qu'il ne **dépassera
pas** (limits), que le noyau lui impose. Dans ce cours, vous regardez un Pod
sans budget, vous donnez un budget à chaque conteneur d'un Pod, vous lisez ce
que le noyau applique vraiment, vous voyez les classes de qualité de service,
puis vous faites dépasser sa limite de mémoire à un conteneur.

Vous travaillez dans un namespace d'essai, `essai-budgets`, avec les Pods
`libre`, `borne`, `garanti` et `gourmand`. Le challenge vous demandera d'autres
budgets, sur un autre Pod, dans un autre namespace : vous le ferez seul, à la
fin.

Page associée : [Requests et limits](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/requests-limits/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-pod-resources-labels
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : un Pod sans budget

Créez le namespace d'essai et un Pod `libre`, sans aucun budget :

```bash
kubectl create namespace essai-budgets
kubectl run libre --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-budgets -- sh -c 'sleep 3600'; kubectl wait --for=condition=Ready pod/libre -n essai-budgets --timeout=60s
```

```text
namespace/essai-budgets created
pod/libre created
pod/libre condition met
```

Regardez ses ressources et sa classe de qualité de service (QoS) :

```bash
kubectl get pod libre -n essai-budgets -o jsonpath='resources={.spec.containers[0].resources} qos={.status.qosClass}{"\n"}'
```

```text
resources={} qos=BestEffort
```

Aucun budget, donc la classe `BestEffort` : le Pod prend ce qui reste. Le noyau
range chaque conteneur dans un **cgroup**, un groupe dont il borne les
ressources. Les limites se lisent depuis l'intérieur du conteneur :

```bash
kubectl exec libre -n essai-budgets -- cat /sys/fs/cgroup/memory.max /sys/fs/cgroup/cpu.max
```

```text
max
max 100000
```

`max` partout : aucune limite, ni de mémoire ni de CPU.

## 📚 Exercice 2 : un budget par conteneur

Les budgets se déclarent **conteneur par conteneur**, dans un bloc
`resources`, avec `requests` et `limits`. Créez un Pod `borne` à deux
conteneurs. Les unités comptent : `150m` veut dire 150 millièmes de CPU, soit
0,15 cœur, et `48Mi` veut dire 48 mébioctets.

```bash
cat <<'YAML' | kubectl apply -n essai-budgets -f -
apiVersion: v1
kind: Pod
metadata:
  name: borne
spec:
  containers:
    - name: site
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      resources:
        requests:
          cpu: 150m
          memory: 48Mi
        limits:
          cpu: 300m
          memory: 96Mi
    - name: compteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "while true; do sleep 5; done"]
      resources:
        requests:
          cpu: 20m
          memory: 16Mi
        limits:
          cpu: 50m
          memory: 24Mi
YAML
kubectl wait --for=condition=Ready pod/borne -n essai-budgets --timeout=120s
```

```text
pod/borne created
pod/borne condition met
```

Le conteneur `compteur` tourne en boucle : une image busybox sans commande
s'arrêterait aussitôt. Relisez les budgets :

```bash
kubectl get pod borne -n essai-budgets -o jsonpath='{range .spec.containers[*]}{.name}: demande {.resources.requests.cpu} et {.resources.requests.memory}, limite {.resources.limits.cpu} et {.resources.limits.memory}{"\n"}{end}'
```

```text
site: demande 150m et 48Mi, limite 300m et 96Mi
compteur: demande 20m et 16Mi, limite 50m et 24Mi
```

## 📚 Exercice 3 : ce que le noyau applique

Une limite n'est pas un vœu : le noyau l'applique. Lisez le cgroup de chaque
conteneur (`-c` choisit le conteneur) :

```bash
for c in site compteur; do echo "$c : memory.max=$(kubectl exec borne -n essai-budgets -c $c -- cat /sys/fs/cgroup/memory.max) cpu.max=$(kubectl exec borne -n essai-budgets -c $c -- cat /sys/fs/cgroup/cpu.max)"; done
```

```text
site : memory.max=100663296 cpu.max=30000 100000
compteur : memory.max=25165824 cpu.max=5000 100000
```

La mémoire est en octets. Le shell fait la conversion :

```bash
echo "96Mi = $((96*1024*1024)) octets, 24Mi = $((24*1024*1024)) octets"
```

```text
96Mi = 100663296 octets, 24Mi = 25165824 octets
```

Les deux nombres correspondent. Pour le CPU, `30000 100000` veut dire « 30 000
microsecondes de calcul par tranche de 100 000 » : 30 % d'un cœur, soit les
`300m` déclarés. Et `5000 100000` font 5 %, soit `50m`.

## 📚 Exercice 4 : la classe de qualité de service

Créez un Pod `garanti` dont les requests sont **égales** aux limits :

```bash
cat <<'YAML' | kubectl apply -n essai-budgets -f -
apiVersion: v1
kind: Pod
metadata:
  name: garanti
spec:
  containers:
    - name: site
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 100m
          memory: 64Mi
YAML
kubectl wait --for=condition=Ready pod/garanti -n essai-budgets --timeout=120s
```

```text
pod/garanti created
pod/garanti condition met
```

Comparez la classe des trois Pods :

```bash
kubectl get pods -n essai-budgets -o custom-columns=POD:.metadata.name,QOS:.status.qosClass
```

```text
POD       QOS
borne     Burstable
garanti   Guaranteed
libre     BestEffort
```

- `Guaranteed` : requests égales aux limits, pour chaque conteneur ;
- `Burstable` : un budget, mais des limits au-dessus des requests ;
- `BestEffort` : aucun budget.

Quand un nœud manque de mémoire, Kubernetes expulse d'abord les Pods
`BestEffort`, puis les `Burstable`, et les `Guaranteed` en dernier.

## 📚 Exercice 5 : dépasser sa limite de mémoire

Le Pod `gourmand` a 64 Mio de limite, et sa commande essaie d'en remplir 200
(`head -c 200m /dev/zero | tail` garde tout en mémoire) :

```bash
cat <<'YAML' | kubectl apply -n essai-budgets -f -
apiVersion: v1
kind: Pod
metadata:
  name: gourmand
spec:
  restartPolicy: Never
  containers:
    - name: appetit
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo je remplis la memoire; head -c 200m /dev/zero | tail"]
      resources:
        requests:
          memory: 32Mi
        limits:
          memory: 64Mi
YAML
```

```text
pod/gourmand created
```

15 secondes plus tard :

```bash
sleep 15; kubectl get pod gourmand -n essai-budgets
kubectl get pod gourmand -n essai-budgets -o jsonpath='{.status.containerStatuses[0].state.terminated.reason} {.status.containerStatuses[0].state.terminated.exitCode}{"\n"}'
```

```text
NAME       READY   STATUS      RESTARTS   AGE
gourmand   0/1     OOMKilled   0          15s
OOMKilled 137
```

`OOMKilled` : le noyau a tué le conteneur parce qu'il dépassait sa limite de
mémoire (OOM veut dire « out of memory »). Le code 137 signale un arrêt forcé.
Pour le CPU, c'est différent : un conteneur qui dépasse sa limite de CPU est
ralenti, pas tué.

## 🧹 Nettoyage

Supprimez le namespace d'essai, avec ses Pods :

```bash
kubectl delete namespace essai-budgets
```

```text
namespace "essai-budgets" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-pod-resources-labels
dsoxlab check ckad-pod-resources-labels
```

```text
╭─ Résultat : ckad-pod-resources-labels ─╮
│  0 / 100 pts                           │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests       │
╰────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un autre Pod à deux conteneurs, avec ses propres
budgets, que le noyau doit appliquer.

```bash
dsoxlab run ckad-pod-resources-labels
dsoxlab challenge ckad-pod-resources-labels
```
