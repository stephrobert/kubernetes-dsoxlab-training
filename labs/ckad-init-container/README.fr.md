# Attendre une dépendance avec un init container

Un **init container** est un conteneur qui s'exécute **avant** les conteneurs
principaux d'un Pod, jusqu'au bout. Tant qu'il n'a pas réussi, les conteneurs
principaux ne démarrent pas. On s'en sert pour préparer quelque chose, ou pour
attendre qu'une dépendance réponde. Dans ce cours, vous écrivez un init
container qui prépare un fichier, vous voyez qu'un Service peut exister sans
personne derrière, vous faites attendre un Pod, vous faites arriver sa
dépendance, puis vous voyez ce qui se passe quand un init container échoue.

Vous travaillez dans un namespace d'essai, `essai-init`, avec une application
`boutique` qui attend un service `stock-svc`. Le challenge vous demandera la
même chose avec d'autres noms, dans un autre namespace : vous le ferez seul, à
la fin.

Page associée : [Init containers et sidecars](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/init-containers-sidecars/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-init-container
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : un init container qui réussit

Créez le namespace d'essai, puis un Pod `preparation`. Son init container
`ecrire-page` écrit une page dans un volume partagé (`emptyDir`). Le conteneur
principal `web`, un nginx, sert ce même volume. Les init containers se
déclarent sous `initContainers`, à côté de `containers` :

```bash
kubectl create namespace essai-init
cat <<'YAML' | kubectl apply -n essai-init -f -
apiVersion: v1
kind: Pod
metadata:
  name: preparation
spec:
  initContainers:
    - name: ecrire-page
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo page preparee par l init container > /travail/index.html"]
      volumeMounts:
        - name: travail
          mountPath: /travail
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      volumeMounts:
        - name: travail
          mountPath: /usr/share/nginx/html
  volumes:
    - name: travail
      emptyDir: {}
YAML
```

```text
namespace/essai-init created
pod/preparation created
```

Attendez que le Pod soit prêt :

```bash
kubectl wait --for=condition=Ready pod/preparation -n essai-init --timeout=120s; kubectl get pod preparation -n essai-init
```

```text
pod/preparation condition met
NAME          READY   STATUS    RESTARTS   AGE
preparation   1/1     Running   0          1s
```

`READY 1/1` ne compte que le conteneur principal. L'état de l'init container
se lit dans `status.initContainerStatuses` :

```bash
kubectl get pod preparation -n essai-init -o jsonpath='{.status.initContainerStatuses[0].name} {.status.initContainerStatuses[0].state.terminated.reason} {.status.initContainerStatuses[0].state.terminated.exitCode}{"\n"}'
```

```text
ecrire-page Completed 0
```

Il est terminé (`Completed`), avec le code 0. Le conteneur principal sert bien
la page qu'il a écrite :

```bash
kubectl exec preparation -n essai-init -c web -- cat /usr/share/nginx/html/index.html
```

```text
page preparee par l init container
```

## 📚 Exercice 2 : un Service sans personne derrière

Créez un Service `stock-svc` qui sélectionne les Pods `app=stock`.
`kubectl create service` met par défaut le sélecteur `app: stock-svc` : `sed`
le remplace par `app: stock` avant l'envoi :

```bash
kubectl create service clusterip stock-svc --tcp=80:80 -n essai-init -o yaml --dry-run=client | sed 's/app: stock-svc/app: stock/' | kubectl apply -f - -n essai-init
kubectl get endpointslices -n essai-init -l kubernetes.io/service-name=stock-svc
```

```text
service/stock-svc created
NAME              ADDRESSTYPE   PORTS     ENDPOINTS   AGE
stock-svc-jhcjx   IPv4          <unset>   <unset>     0s
```

Aucun Pod ne porte `app=stock` : le Service n'a aucune adresse derrière lui
(`<unset>`). Lancez un Pod jetable qui interroge ce Service par son nom DNS,
puis en HTTP (`--rm` le supprime à la fin) :

```bash
kubectl run sonde --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --restart=Never -n essai-init --rm -i --quiet -- sh -c 'nslookup stock-svc.essai-init.svc.cluster.local | tail -3; wget -qO- -T 3 http://stock-svc/ || echo "wget : code $?"'
```

```text
Name:	stock-svc.essai-init.svc.cluster.local
Address: 10.100.162.100

wget: can't connect to remote host (10.100.162.100): Connection refused
wget : code 1
```

Le nom se résout : le Service existe dans le DNS dès sa création. Mais la
requête HTTP est refusée, car personne ne répond derrière. Attendre que le nom
se résolve n'attend donc rien. Il faut attendre une **réponse**.

## 📚 Exercice 3 : un init container qui attend

Créez le Pod `boutique`. Son init container `attendre-stock` répète une
requête HTTP vers `stock-svc` toutes les 3 secondes (`until … do … done`),
jusqu'à ce qu'elle réussisse :

```bash
cat <<'YAML' | kubectl apply -n essai-init -f -
apiVersion: v1
kind: Pod
metadata:
  name: boutique
spec:
  initContainers:
    - name: attendre-stock
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "until wget -qO- -T 2 http://stock-svc/ > /dev/null; do echo stock-svc ne repond pas encore; sleep 3; done; echo stock-svc repond"]
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
YAML
```

```text
pod/boutique created
```

Après 15 secondes, regardez le Pod :

```bash
sleep 15; kubectl get pod boutique -n essai-init
```

```text
NAME       READY   STATUS     RESTARTS   AGE
boutique   0/1     Init:0/1   0          15s
```

`Init:0/1` : 0 init container terminé sur 1. Ses journaux montrent qu'il
attend :

```bash
kubectl logs boutique -n essai-init -c attendre-stock | tail -3
```

```text
stock-svc ne repond pas encore
wget: can't connect to remote host (10.100.162.100): Connection refused
stock-svc ne repond pas encore
```

Et le conteneur principal n'a pas démarré du tout :

```bash
kubectl logs boutique -n essai-init -c web 2>&1 | tail -1
```

```text
Error from server (BadRequest): container "web" in pod "boutique" is waiting to start: PodInitializing
```

## 📚 Exercice 4 : la dépendance arrive

Lancez un Pod nginx `stock` avec le label `app=stock` :

```bash
kubectl run stock --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb --labels=app=stock --port=80 -n essai-init; kubectl wait --for=condition=Ready pod/stock -n essai-init --timeout=120s
kubectl get endpointslices -n essai-init -l kubernetes.io/service-name=stock-svc
```

```text
pod/stock created
pod/stock condition met
NAME              ADDRESSTYPE   PORTS   ENDPOINTS      AGE
stock-svc-jhcjx   IPv4          80      10.244.38.87   20s
```

Le Service a maintenant une adresse. Sans rien toucher d'autre, attendez que
`boutique` soit prêt :

```bash
kubectl wait --for=condition=Ready pod/boutique -n essai-init --timeout=120s; kubectl get pod boutique -n essai-init
```

```text
pod/boutique condition met
NAME       READY   STATUS    RESTARTS   AGE
boutique   1/1     Running   0          17s
```

L'init container a vu la réponse, s'est terminé, et le conteneur principal a
démarré :

```bash
kubectl logs boutique -n essai-init -c attendre-stock | tail -2
kubectl get pod boutique -n essai-init -o jsonpath='{.status.initContainerStatuses[0].state.terminated.reason} {.status.initContainerStatuses[0].state.terminated.exitCode}{"\n"}'
```

```text
stock-svc ne repond pas encore
stock-svc repond
Completed 0
```

## 📚 Exercice 5 : un init container qui échoue

Que se passe-t-il si l'init container sort en erreur ? Créez un Pod `rate`
dont l'init container sort avec le code 1 :

```bash
cat <<'YAML' | kubectl apply -n essai-init -f -
apiVersion: v1
kind: Pod
metadata:
  name: rate
spec:
  initContainers:
    - name: verifier
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo verification impossible; exit 1"]
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
YAML
```

```text
pod/rate created
```

Après 25 secondes :

```bash
sleep 25; kubectl get pod rate -n essai-init
kubectl get pod rate -n essai-init -o jsonpath='{.status.initContainerStatuses[0].restartCount}{"\n"}'; kubectl logs rate -n essai-init -c verifier
```

```text
NAME   READY   STATUS       RESTARTS      AGE
rate   0/1     Init:Error   2 (24s ago)   25s
2
verification impossible
```

`Init:Error` : l'init container a échoué. Kubernetes le relance (déjà 2 fois),
et le conteneur principal attend toujours. Un init container doit donc
**réussir** pour que le Pod démarre. C'est ce qui permet de bloquer une
application tant que sa dépendance manque.

## 🧹 Nettoyage

Supprimez le namespace d'essai, et tout ce qu'il contient :

```bash
kubectl delete namespace essai-init
```

```text
namespace "essai-init" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-init-container
dsoxlab check ckad-init-container
```

```text
╭─ Résultat : ckad-init-container ──╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une autre application, qui doit attendre son serveur
de configuration avant de démarrer.

```bash
dsoxlab run ckad-init-container
dsoxlab challenge ckad-init-container
```
