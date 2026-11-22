# Isoler une charge sensible dans un bac à sable gVisor

La leçon montre comment gVisor interpose un noyau applicatif entre le
conteneur et la machine, et comment une RuntimeClass y dirige un Pod. Ce cours
ajoute trois cas qu'elle ne fait que citer : un handler que le nœud ne
connaît pas et l'événement qui le dit, le démarrage du noyau de gVisor vu de
l'intérieur du Pod, et le coût du bac à sable déclaré au Pod par le champ
`overhead`.

Vous travaillez dans le namespace `essai-sandbox`, avec deux RuntimeClass
d'essai. Le challenge porte sur une autre RuntimeClass et d'autres Pods : vous
le ferez seul, à la fin.

Page associée : [Runtime Sandboxes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/runtime-sandboxes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-runtime-sandbox-gvisor
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). containerd y connaît un second runtime, `runsc`,
celui de gVisor. Les Pods de ce cours sont placés sur `k8s-cp.lab`
(`nodeName`), le seul nœud où il est installé.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
22 novembre 2026.

## 🧭 Exercice 1 : un handler que le nœud ne connaît pas

Une RuntimeClass associe un nom à un **handler**, le nom du runtime dans la
configuration de containerd. Rien ne vérifie ce nom à la création. Créez une
RuntimeClass dont le handler n'existe pas, et un Pod qui s'en sert :

```bash
kubectl create namespace essai-sandbox; cat <<'YAML' | kubectl apply -f -
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: essai-faux
handler: runsc-absent
YAML
kubectl run mal-route -n essai-sandbox --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --overrides='{"spec":{"nodeName":"k8s-cp.lab","runtimeClassName":"essai-faux"}}' -- sleep 3600; sleep 15; kubectl get pod mal-route -n essai-sandbox
```

```text
namespace/essai-sandbox created
runtimeclass.node.k8s.io/essai-faux created
pod/mal-route created
NAME        READY   STATUS              RESTARTS   AGE
mal-route   0/1     ContainerCreating   0          15s
```

L'API server accepte tout, et le Pod reste en `ContainerCreating`. La raison
est dans les événements du Pod :

```bash
kubectl get events -n essai-sandbox --field-selector involvedObject.name=mal-route,reason=FailedCreatePodSandBox -o custom-columns=RAISON:.reason,MESSAGE:.message --no-headers | tail -1 | cut -c1-320
```

```text
FailedCreatePodSandBox   Failed to create pod sandbox: rpc error: code = Unknown desc = unable to get OCI runtime for sandbox "4e3edc2894634cbf25afd52893970c884fd50dd7ebcd5122b14d3badcc42ea44": no runtime for "runsc-absent" is configured
```

`no runtime for "runsc-absent" is configured` : c'est containerd, sur le nœud,
qui ne connaît pas ce handler. Un Pod bloqué en `ContainerCreating` derrière
une RuntimeClass se diagnostique là, pas dans les journaux de l'application.

## 🛡️ Exercice 2 : le noyau de gVisor, vu de l'intérieur

Créez une RuntimeClass d'essai vers le vrai handler `runsc`, avec un champ
`overhead` qui servira à l'exercice suivant. Lancez un Pod qui s'en sert, et
un Pod ordinaire :

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: essai-bac
handler: runsc
overhead:
  podFixed:
    memory: 64Mi
    cpu: 100m
YAML
kubectl run bac -n essai-sandbox --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --overrides='{"spec":{"nodeName":"k8s-cp.lab","runtimeClassName":"essai-bac"}}' -- sleep 3600; kubectl run hote -n essai-sandbox --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --overrides='{"spec":{"nodeName":"k8s-cp.lab"}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/bac pod/hote -n essai-sandbox --timeout=120s
```

```text
runtimeclass.node.k8s.io/essai-bac created
pod/bac created
pod/hote created
pod/bac condition met
pod/hote condition met
```

Demandez à chacun le journal de démarrage du noyau, avec `dmesg` :

```bash
for p in hote bac; do echo "--- $p"; kubectl exec $p -n essai-sandbox -- dmesg 2>&1 | head -3; done
```

```text
--- hote
dmesg: klogctl: Operation not permitted
command terminated with exit code 1
--- bac
[   0.000000] Starting gVisor...
[   0.579025] Rewriting the kernel in Rust...
[   0.654146] Letting the watchdogs out...
```

Le Pod ordinaire n'a pas le droit de lire le journal du noyau de la machine.
Le Pod du bac à sable, lui, lit celui de **son propre** noyau : le Sentry de
gVisor, qui écrit au démarrage ces lignes fantaisistes. Ses appels système
n'atteignent jamais le noyau de la machine : c'est le Sentry qui y répond.

## 💰 Exercice 3 : le coût du bac à sable, déclaré au Pod

Un bac à sable consomme de la mémoire et du processeur en plus du conteneur.
Le champ `overhead` de la RuntimeClass le déclare, et l'admission le recopie
dans chaque Pod qui s'en sert. Comparez les deux Pods :

```bash
for p in hote bac; do printf '%-5s runtimeClass=%-10s overhead=%s\n' $p "$(kubectl get pod $p -n essai-sandbox -o jsonpath='{.spec.runtimeClassName}')" "$(kubectl get pod $p -n essai-sandbox -o jsonpath='{.spec.overhead}')"; done
```

```text
hote  runtimeClass=           overhead=
bac   runtimeClass=essai-bac  overhead={"cpu":"100m","memory":"64Mi"}
```

Le Pod du bac à sable porte `overhead` : 100m de processeur et 64Mi de
mémoire, que le scheduler ajoute à ses demandes pour choisir un nœud et que
les quotas comptent. Le Pod ordinaire n'en a pas. Sans ce champ, un nœud
rempli de Pods en bac à sable serait surchargé par des coûts que personne
n'a déclarés.

## 🧹 Nettoyage

Supprimez le namespace d'essai, puis les deux RuntimeClass, qui ne sont pas
rattachées à un namespace :

```bash
kubectl delete namespace essai-sandbox --wait=true --timeout=120s; kubectl delete runtimeclass essai-bac essai-faux
```

```text
namespace "essai-sandbox" deleted
runtimeclass.node.k8s.io "essai-bac" deleted
runtimeclass.node.k8s.io "essai-faux" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-runtime-sandbox-gvisor
dsoxlab check cks-runtime-sandbox-gvisor
```

```text
╭─ Résultat : cks-runtime-sandbox-gvisor ─╮
│  0 / 100 pts                            │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests        │
╰─────────────────────────────────────────╯
```

0 sur 2 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : déclarer gVisor au cluster et y faire tourner un Pod
sensible, avec la preuve qu'il ne voit pas le noyau de la machine.

```bash
dsoxlab run cks-runtime-sandbox-gvisor
dsoxlab challenge cks-runtime-sandbox-gvisor
```
