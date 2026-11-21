# Trois Pods en CrashLoopBackOff, trois causes

La leçon montre comment trouver pourquoi un conteneur redémarre en boucle. Ce
cours ajoute des causes que la leçon ne montre pas : une sonde de vie qui tue
une application lente à démarrer, un programme qui réussit et boucle quand
même, un `command` qui remplace le programme prévu par l'image, et le message
de fin qu'un conteneur peut laisser pour expliquer son arrêt.

Vous travaillez dans un namespace d'essai, `essai-relance`, avec des Pods
d'essai. Le challenge porte sur trois autres Pods : vous le ferez seul, à la
fin.

Page associée : [CrashLoopBackOff](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/crashloopbackoff-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-troubleshoot-crashloop
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

## 🐢 Exercice 1 : une sonde de vie qui tue une application lente

Créez un Pod nginx qui attend 25 secondes avant de démarrer, avec une sonde de
vie qui le déclare mort après 2 échecs espacés de 5 secondes. La commande
attend 50 secondes, puis lit l'événement `Killing` :

```bash
kubectl create namespace essai-relance; cat <<YAML | kubectl apply -n essai-relance -f -
apiVersion: v1
kind: Pod
metadata:
  name: lent
spec:
  containers:
    - name: lent
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      command: ["sh", "-c", "sleep 25; exec nginx -g 'daemon off;'"]
      livenessProbe:
        httpGet: {path: /, port: 80}
        periodSeconds: 5
        failureThreshold: 2
YAML
sleep 50; kubectl get pod lent -n essai-relance; kubectl get events -n essai-relance --field-selector involvedObject.name=lent,reason=Killing -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
namespace/essai-relance created
pod/lent created
NAME   READY   STATUS    RESTARTS      AGE
lent   1/1     Running   1 (10s ago)   50s
Container lent failed liveness probe, will be restarted
```

Un redémarrage : la sonde a échoué pendant les 25 secondes de démarrage, et le
kubelet a tué le conteneur. Une sonde de vie trop pressée fait redémarrer en
boucle une application saine mais lente. Recréez le Pod avec une sonde de
démarrage (`startupProbe`) qui lui laisse une minute (12 essais de
5 secondes) :

```bash
kubectl delete pod lent -n essai-relance; cat <<YAML | kubectl apply -n essai-relance -f -
apiVersion: v1
kind: Pod
metadata:
  name: lent
spec:
  containers:
    - name: lent
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      command: ["sh", "-c", "sleep 25; exec nginx -g 'daemon off;'"]
      startupProbe:
        httpGet: {path: /, port: 80}
        periodSeconds: 5
        failureThreshold: 12
      livenessProbe:
        httpGet: {path: /, port: 80}
        periodSeconds: 5
        failureThreshold: 2
YAML
sleep 50; kubectl get pod lent -n essai-relance
```

```text
pod "lent" deleted from essai-relance namespace
pod/lent created
NAME   READY   STATUS    RESTARTS   AGE
lent   1/1     Running   0          50s
```

Aucun redémarrage. Tant que la sonde de démarrage n'a pas réussi, la sonde de
vie ne joue pas.

## ✅ Exercice 2 : un programme qui réussit, et boucle quand même

Lancez un Pod dont le programme fait son travail et sort avec le code 0 :

```bash
kubectl run sage --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-relance -- sh -c 'echo travail fini; exit 0'; sleep 45; kubectl get pod sage -n essai-relance; kubectl get pod sage -n essai-relance -o jsonpath='dernier code={.status.containerStatuses[0].lastState.terminated.exitCode} raison={.status.containerStatuses[0].lastState.terminated.reason}{"\n"}'
```

```text
pod/sage created
NAME   READY   STATUS      RESTARTS      AGE
sage   0/1     Completed   3 (33s ago)   45s
dernier code=0 raison=Completed
```

Trois redémarrages, sans aucune erreur : le dernier code est 0. Un Pod relance
son conteneur dès qu'il s'arrête, même avec succès (`restartPolicy: Always`
par défaut). Un travail qui doit finir et s'arrêter se lance dans un Job, pas
dans un Pod ou un Deployment.

## 🧩 Exercice 3 : command remplace le programme de l'image

Lancez nginx en lui donnant une commande avec `--command`, ici `nginx -v` :

```bash
kubectl run entete --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-relance --command -- nginx -v; sleep 8; kubectl logs entete -n essai-relance; kubectl get pod entete -n essai-relance -o jsonpath='{.status.containerStatuses[0].state}{"\n"}' | cut -c1-80
```

```text
pod/entete created
nginx version: nginx/1.30.5
{"waiting":{"message":"back-off 10s restarting failed container=entete pod=entet
```

Le conteneur affiche la version, sort, et part en boucle. Regardez ce que
contient le Pod :

```bash
kubectl get pod entete -n essai-relance -o jsonpath='command={.spec.containers[0].command} args={.spec.containers[0].args}{"\n"}'
```

```text
command=["nginx","-v"] args=
```

`command` remplace le point d'entrée de l'image : nginx n'est pas lancé en
serveur, seule la commande demandée tourne. `args`, lui, ne fait que
compléter le point d'entrée. Un `command` mal choisi donne un conteneur qui
« fonctionne » une seconde, puis s'arrête.

## 💬 Exercice 4 : le message de fin écrit par le conteneur

Un conteneur peut écrire une explication dans `/dev/termination-log` avant de
s'arrêter. Kubernetes la recopie dans l'état du Pod :

```bash
cat <<YAML | kubectl apply -n essai-relance -f -
apiVersion: v1
kind: Pod
metadata:
  name: message
spec:
  restartPolicy: Never
  containers:
    - name: m
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo 'base injoignable : essai-db:5432' > /dev/termination-log; exit 2"]
YAML
sleep 10; kubectl get pod message -n essai-relance -o jsonpath='{.status.containerStatuses[0].state.terminated.message}{"\n"}'
```

```text
pod/message created
base injoignable : essai-db:5432
```

Le message est lisible sans les journaux, directement dans l'état du Pod.
Pour une application qui n'écrit rien dans ce fichier,
`terminationMessagePolicy: FallbackToLogsOnError` reprend la fin de ses
journaux en cas d'erreur :

```bash
kubectl run message-journal --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-relance --restart=Never --overrides='{"spec":{"containers":[{"name":"m","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sh","-c","echo derniere ligne du journal; exit 2"],"terminationMessagePolicy":"FallbackToLogsOnError"}]}}'; sleep 10; kubectl get pod message-journal -n essai-relance -o jsonpath='{.status.containerStatuses[0].state.terminated.message}{"\n"}'
```

```text
pod/message-journal created
derniere ligne du journal
```

La dernière ligne du journal est devenue le message de fin. C'est utile quand
les journaux du conteneur ont déjà disparu.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-relance
```

```text
namespace "essai-relance" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-troubleshoot-crashloop
dsoxlab check ckad-troubleshoot-crashloop
```

```text
╭─ Résultat : ckad-troubleshoot-crashloop ─╮
│  0 / 100 pts                             │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests         │
╰──────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : trois Pods en boucle, chacun pour une raison
différente, à remettre en marche.

```bash
dsoxlab run ckad-troubleshoot-crashloop
dsoxlab challenge ckad-troubleshoot-crashloop
```
