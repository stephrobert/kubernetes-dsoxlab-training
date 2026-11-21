# Observer la lecture d'un fichier sensible avec Tetragon, puis la bloquer

La leçon compare Falco et Tetragon sur un même scénario : lire un fichier
sensible. Tetragon l'observe, puis le bloque avec une `TracingPolicy`. Ce
cours ajoute des cas que la leçon ne montre pas : un fichier monté dans un Pod,
que Tetragon ne voit pas sous le nom qu'on croit ; la différence entre les
événements à venir et l'historique ; et l'événement que laisse un blocage.

Vous travaillez dans un namespace d'essai, `essai-tg`, avec un Pod `curieux`
qui monte un ConfigMap en `/etc/essai/`. Le challenge porte sur d'autres
objets : vous le ferez seul, à la fin.

Page associée : [Falco vs Tetragon : comparés sur le même cluster](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/falco-vs-tetragon/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-observer-et-bloquer-avec-tetragon
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà. La préparation du lab
a installé Tetragon, avec un agent par nœud.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2 et Tetragon 1.8.0. La leçon montre
la 1.7.1 : les politiques s'écrivent de la même façon.

Créez le Pod d'essai et son ConfigMap :

```bash
kubectl create namespace essai-tg; kubectl -n essai-tg create configmap reglages --from-literal=niveau=debug; kubectl -n essai-tg run curieux --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --overrides='{"spec":{"containers":[{"name":"curieux","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","infinity"],"volumeMounts":[{"name":"r","mountPath":"/etc/essai"}]}],"volumes":[{"name":"r","configMap":{"name":"reglages"}}]}}'; kubectl -n essai-tg wait --for=condition=Ready pod/curieux --timeout=120s
```

```text
namespace/essai-tg created
configmap/reglages created
pod/curieux created
pod/curieux condition met
```

Les commandes des exercices trouvent l'agent Tetragon du nœud où tourne
`curieux` (un agent ne voit que son nœud), lisent ses événements JSON dans le
conteneur `export-stdout`, et n'affichent que ceux de `curieux`.

## 🙈 Exercice 1 : Equal ne voit pas un fichier monté

Posez une politique qui observe l'ouverture de `/etc/essai/niveau`, avec
l'opérateur `Equal` de la leçon, lisez le fichier, puis comptez les
événements :

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: essai-egal
spec:
  kprobes:
    - call: security_file_open
      syscall: false
      args:
        - index: 0
          type: file
      selectors:
        - matchArgs:
            - index: 0
              operator: Equal
              values:
                - /etc/essai/niveau
YAML
sleep 5; kubectl -n essai-tg exec curieux -- cat /etc/essai/niveau; echo; sleep 5; AG=$(kubectl -n kube-system get pods -l app.kubernetes.io/name=tetragon --field-selector spec.nodeName=$(kubectl -n essai-tg get pod curieux -o jsonpath='{.spec.nodeName}') -o jsonpath='{.items[0].metadata.name}'); kubectl -n kube-system logs $AG -c export-stdout --since=20s | python3 -c 'import json,sys
for l in sys.stdin:
    e = json.loads(l).get("process_kprobe")
    if e and e["process"].get("pod", {}).get("name") == "curieux":
        print(e["policy_name"], e["action"], e["process"]["binary"], [a.get("file_arg", {}).get("path") for a in e["args"]])' | wc -l
```

```text
tracingpolicy.cilium.io/essai-egal created
debug
0
```

Le fichier se lit, mais Tetragon ne rapporte **aucun** événement. Regardez
comment Kubernetes monte un ConfigMap :

```bash
kubectl -n essai-tg exec curieux -- ls -la /etc/essai/ | tail -3
```

```text
drwxr-xr-x    2 root     root          4096 Nov 21 18:48 ..2026_11_21_18_48_46.1301310973
lrwxrwxrwx    1 root     root            32 Nov 21 18:48 ..data -> ..2026_11_21_18_48_46.1301310973
lrwxrwxrwx    1 root     root            13 Nov 21 18:48 niveau -> ..data/niveau
```

`niveau` est un lien vers `..data/niveau`, lui-même un lien vers un répertoire
horodaté. Le noyau ouvre le **vrai** fichier, au bout de la chaîne. Le chemin
que vous voyez n'est donc jamais celui que Tetragon compare : un `Equal` sur
un fichier monté depuis un ConfigMap ou un Secret ne correspond jamais.

## 🎯 Exercice 2 : Prefix voit le chemin réel

Remplacez la politique par une autre, qui vise tout ce qui commence par
`/etc/essai/` :

```bash
kubectl delete tracingpolicy essai-egal; cat <<'YAML' | kubectl apply -f -
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: essai-prefixe
spec:
  kprobes:
    - call: security_file_open
      syscall: false
      args:
        - index: 0
          type: file
      selectors:
        - matchArgs:
            - index: 0
              operator: Prefix
              values:
                - /etc/essai/
YAML
sleep 5; kubectl -n essai-tg exec curieux -- cat /etc/essai/niveau; echo; sleep 5; AG=$(kubectl -n kube-system get pods -l app.kubernetes.io/name=tetragon --field-selector spec.nodeName=$(kubectl -n essai-tg get pod curieux -o jsonpath='{.spec.nodeName}') -o jsonpath='{.items[0].metadata.name}'); kubectl -n kube-system logs $AG -c export-stdout --since=20s | python3 -c 'import json,sys
for l in sys.stdin:
    e = json.loads(l).get("process_kprobe")
    if e and e["process"].get("pod", {}).get("name") == "curieux":
        print(e["policy_name"], e["action"], e["process"]["binary"], [a.get("file_arg", {}).get("path") for a in e["args"]])'
```

```text
tracingpolicy.cilium.io "essai-egal" deleted
tracingpolicy.cilium.io/essai-prefixe created
debug
essai-prefixe KPROBE_ACTION_POST /bin/cat ['/etc/essai/..2026_11_21_18_48_46.1301310973/niveau']
```

Cette fois, l'événement arrive : la politique, l'action (`KPROBE_ACTION_POST`,
une observation seule), le binaire, et le chemin réel du fichier, avec son
répertoire horodaté. `Prefix` couvre le répertoire monté, quel que soit le
nom du répertoire caché.

## 📡 Exercice 3 : tetra getevents ne voit que l'avenir

`tetra getevents` interroge l'agent en direct. Lancez-le sur `curieux`
pendant 10 secondes, sans rien faire dans le Pod :

```bash
AG=$(kubectl -n kube-system get pods -l app.kubernetes.io/name=tetragon --field-selector spec.nodeName=$(kubectl -n essai-tg get pod curieux -o jsonpath='{.spec.nodeName}') -o jsonpath='{.items[0].metadata.name}'); kubectl -n kube-system exec $AG -c tetragon -- timeout 10 tetra getevents -o compact --pods curieux | wc -l
```

```text
0
```

Zéro ligne : la lecture de l'exercice 2 est déjà passée, et `tetra getevents`
ne montre que ce qui arrive pendant qu'il écoute. Relancez-le, avec une
lecture faite pendant l'écoute. Le `sed` retire les pictogrammes du début des
lignes :

```bash
AG=$(kubectl -n kube-system get pods -l app.kubernetes.io/name=tetragon --field-selector spec.nodeName=$(kubectl -n essai-tg get pod curieux -o jsonpath='{.spec.nodeName}') -o jsonpath='{.items[0].metadata.name}'); (sleep 4; kubectl -n essai-tg exec curieux -- head -c 3 /etc/essai/niveau > /dev/null) & kubectl -n kube-system exec $AG -c tetragon -- timeout 12 tetra getevents -o compact --pods curieux 2>&1 | grep -E 'head|security_file_open' | sed 's/^[^a-z]*//' | cut -c1-120
```

```text
process essai-tg/curieux /bin/head "-c 3 /etc/essai/niveau"
syscall essai-tg/curieux /bin/head security_file_open
exit    essai-tg/curieux /bin/head "-c 3 /etc/essai/niveau" 0
```

Le démarrage de `head`, l'ouverture du fichier repérée par la politique, puis
la fin du processus. Pour relire le passé, ce sont les journaux de
`export-stdout` qu'il faut lire, comme dans les exercices 1 et 2.

## 🛑 Exercice 4 : l'événement d'un blocage

Ajoutez l'action `Sigkill` à la même politique, et relisez le fichier :

```bash
kubectl delete tracingpolicy essai-prefixe; cat <<'YAML' | kubectl apply -f -
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: essai-bloque
spec:
  kprobes:
    - call: security_file_open
      syscall: false
      args:
        - index: 0
          type: file
      selectors:
        - matchArgs:
            - index: 0
              operator: Prefix
              values:
                - /etc/essai/
          matchActions:
            - action: Sigkill
YAML
sleep 5; kubectl -n essai-tg exec curieux -- cat /etc/essai/niveau; echo "code : $?"; sleep 5; AG=$(kubectl -n kube-system get pods -l app.kubernetes.io/name=tetragon --field-selector spec.nodeName=$(kubectl -n essai-tg get pod curieux -o jsonpath='{.spec.nodeName}') -o jsonpath='{.items[0].metadata.name}'); kubectl -n kube-system logs $AG -c export-stdout --since=20s | python3 -c 'import json,sys
for l in sys.stdin:
    e = json.loads(l).get("process_kprobe")
    if e and e["process"].get("pod", {}).get("name") == "curieux":
        print(e["policy_name"], e["action"], e["process"]["binary"], [a.get("file_arg", {}).get("path") for a in e["args"]])'
```

```text
tracingpolicy.cilium.io "essai-prefixe" deleted
tracingpolicy.cilium.io/essai-bloque created
command terminated with exit code 137
code : 137
essai-prefixe KPROBE_ACTION_POST /bin/head ['/etc/essai/..2026_11_21_18_48_46.1301310973/niveau']
essai-bloque KPROBE_ACTION_SIGKILL /bin/cat ['/etc/essai/..2026_11_21_18_48_46.1301310973/niveau']
```

Le processus est tué (code 137), avant d'avoir lu le fichier. L'événement le
dit : action `KPROBE_ACTION_SIGKILL`, avec le binaire et le fichier visés. La
ligne précédente, une observation de l'exercice 3, vient de la fenêtre des 20
dernières secondes : un blocage laisse la même trace qu'une observation, avec
une autre action.

## 🧹 Nettoyage

Retirez la politique d'essai et le namespace. Une `TracingPolicy` oubliée
continuerait de tuer des processus :

```bash
kubectl delete tracingpolicy essai-bloque; kubectl delete namespace essai-tg; kubectl get tracingpolicies
```

```text
tracingpolicy.cilium.io "essai-bloque" deleted
namespace "essai-tg" deleted
No resources found
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-observer-et-bloquer-avec-tetragon
dsoxlab check k8s-observer-et-bloquer-avec-tetragon
```

```text
╭─ Résultat : k8s-observer-et-bloquer-avec-tetragon ─╮
│  0 / 100 pts                                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                   │
╰────────────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une clé d'API montée depuis un Secret, lue en douce
par l'un de deux Pods. Trouvez lequel et avec quel outil, puis bloquez toute
lecture de la clé, et rien d'autre.

```bash
dsoxlab run k8s-observer-et-bloquer-avec-tetragon
dsoxlab challenge k8s-observer-et-bloquer-avec-tetragon
```
