# Réparer le gardien d'une application avec un init container

Un **init container** est un conteneur qui s'exécute **avant** les conteneurs
principaux d'un Pod, jusqu'au bout. Tant qu'il n'a pas réussi, les conteneurs
principaux ne démarrent pas. On s'en sert pour préparer quelque chose, ou pour
attendre qu'une dépendance réponde. Dans ce cours, vous voyez ce que devient
un Pod dont l'init container échoue, selon qu'il est relancé ou non. Vous
voyez aussi qu'un Service peut exister sans personne derrière. Puis vous
écrivez une attente bornée, vous la laissez expirer, et vous faites arriver la
dépendance.

Vous travaillez dans un namespace d'essai, `essai-init`, avec une application
`boutique` qui attend un service `stock-svc`. Le challenge porte sur une autre
application, dans un autre namespace : vous le ferez seul, à la fin.

Page associée : [Init containers et sidecars](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/init-containers-sidecars/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-init-container
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : un init container qui échoue, sans relance

Créez le namespace d'essai, puis un Pod `unique`. Son init container
`verifier` sort avec le code 3. Le Pod déclare `restartPolicy: Never` : rien
n'y est relancé. Les init containers se déclarent sous `initContainers`, à
côté de `containers` :

```bash
kubectl create namespace essai-init
cat <<'YAML' | kubectl apply -n essai-init -f -
apiVersion: v1
kind: Pod
metadata:
  name: unique
spec:
  restartPolicy: Never
  initContainers:
    - name: verifier
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo verification impossible; exit 3"]
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
YAML
```

```text
namespace/essai-init created
apiVersion: v1
kind: Pod
metadata:
  name: unique
spec:
  restartPolicy: Never
  initContainers:
    - name: verifier
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo verification impossible; exit 3"]
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
YAML
pod/unique created
```

Après 10 secondes :

```bash
sleep 10; kubectl get pod unique -n essai-init
```

```text
NAME     READY   STATUS       RESTARTS   AGE
unique   0/1     Init:Error   0          10s
```

`Init:Error` : l'init container a échoué. La phase du Pod, le code de sortie
et le nombre de relances se lisent dans son statut :

```bash
kubectl get pod unique -n essai-init -o jsonpath='{.status.phase} {.status.initContainerStatuses[0].state.terminated.exitCode} {.status.initContainerStatuses[0].restartCount}{"\n"}'
```

```text
Failed 3 0
```

Le Pod est en phase `Failed`, avec le code 3 et aucune relance. 20 secondes
plus tard, rien n'a bougé :

```bash
sleep 20; kubectl get pod unique -n essai-init
```

```text
NAME     READY   STATUS       RESTARTS   AGE
unique   0/1     Init:Error   0          30s
```

Avec `restartPolicy: Never`, un init container en échec fait échouer tout le
Pod, définitivement. Le conteneur `web` ne démarrera jamais.

## 📚 Exercice 2 : un Service sans personne derrière

Créez un Service `stock-svc` qui sélectionne les Pods `app=stock`, sur le
port 80 :

```bash
cat <<'YAML' | kubectl apply -n essai-init -f -
apiVersion: v1
kind: Service
metadata:
  name: stock-svc
spec:
  selector:
    app: stock
  ports:
    - port: 80
      targetPort: 80
YAML
kubectl get endpointslices -n essai-init -l kubernetes.io/service-name=stock-svc
```

```text
apiVersion: v1
kind: Service
metadata:
  name: stock-svc
spec:
  selector:
    app: stock
  ports:
    - port: 80
      targetPort: 80
YAML
service/stock-svc created
NAME              ADDRESSTYPE   PORTS     ENDPOINTS   AGE
stock-svc-qb8zx   IPv4          <unset>   <unset>     0s
```

Aucun Pod ne porte `app=stock` : le Service n'a aucune adresse derrière lui
(`<unset>`). Lancez un Pod jetable qui interroge ce Service par son nom DNS,
puis en HTTP (`--rm` le supprime à la fin) :

```bash
kubectl run sonde --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --restart=Never -n essai-init --rm -i --quiet -- sh -c 'nslookup stock-svc.essai-init.svc.cluster.local | tail -3; wget -qO- -T 3 http://stock-svc/ || echo "wget : code $?"'
```

```text
Name:	stock-svc.essai-init.svc.cluster.local
Address: 10.100.1.209

wget: can't connect to remote host (10.100.1.209): Connection refused
wget : code 1
```

Le nom se résout : le Service existe dans le DNS dès sa création. Mais la
requête HTTP est refusée, car personne ne répond derrière. Attendre que le nom
se résolve n'attend donc rien. Il faut attendre une **réponse**.

## 📚 Exercice 3 : une attente bornée qui expire

Créez le Pod `boutique`. Son init container `attendre-stock` interroge
`stock-svc` en HTTP 5 fois, à 2 secondes d'intervalle. Il sort avec le code 0
dès qu'une requête réussit, et avec le code 1 après le cinquième échec. Une
attente sans limite ne se terminerait jamais, et rien ne signalerait le
problème :

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
      command:
        - sh
        - -c
        - |
          for i in 1 2 3 4 5; do
            wget -qO- -T 2 http://stock-svc/ > /dev/null && echo stock-svc repond && exit 0
            echo essai $i : stock-svc ne repond pas
            sleep 2
          done
          echo abandon apres 5 essais
          exit 1
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
YAML
```

```text
apiVersion: v1
kind: Pod
metadata:
  name: boutique
spec:
  initContainers:
    - name: attendre-stock
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command:
        - sh
        - -c
        - |
          for i in 1 2 3 4 5; do
            wget -qO- -T 2 http://stock-svc/ > /dev/null && echo stock-svc repond && exit 0
            echo essai $i : stock-svc ne repond pas
            sleep 2
          done
          echo abandon apres 5 essais
          exit 1
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
YAML
pod/boutique created
```

Après 25 secondes, regardez le Pod :

```bash
sleep 25; kubectl get pod boutique -n essai-init
```

```text
NAME       READY   STATUS     RESTARTS      AGE
boutique   0/1     Init:0/1   1 (10s ago)   25s
```

`Init:0/1` : 0 init container terminé sur 1. La colonne `RESTARTS` dit que
l'init container a déjà été relancé une fois : la première attente a expiré.
Ce Pod n'a pas de `restartPolicy`, il vaut donc `Always`, et Kubernetes relance
l'init container en échec. `--previous` montre les journaux de la tentative
d'avant :

```bash
kubectl logs boutique -n essai-init -c attendre-stock --previous | tail -2
```

```text
wget: can't connect to remote host (10.100.1.209): Connection refused
abandon apres 5 essais
```

40 secondes plus tard :

```bash
sleep 40; kubectl get pod boutique -n essai-init
```

```text
NAME       READY   STATUS       RESTARTS      AGE
boutique   0/1     Init:Error   2 (34s ago)   65s
```

Une deuxième attente a expiré, et le Pod affiche `Init:Error`. Le compteur de
relances et le code de la dernière sortie le confirment :

```bash
kubectl get pod boutique -n essai-init -o jsonpath='{.status.initContainerStatuses[0].restartCount} {.status.initContainerStatuses[0].lastState.terminated.exitCode}{"\n"}'
```

```text
2 1
```

Une attente bornée se voit : le Pod passe en erreur et ses relances
s'additionnent. Une attente sans limite resterait en `Init:0/1` sans fin, sans
aucune relance.

## 📚 Exercice 4 : la dépendance arrive

Lancez un Pod nginx `stock` avec le label `app=stock` :

```bash
kubectl run stock --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb --labels=app=stock --port=80 -n essai-init; kubectl wait --for=condition=Ready pod/stock -n essai-init --timeout=120s
```

```text
pod/stock created
pod/stock condition met
```

Le Service a maintenant une adresse. Sans rien toucher d'autre, attendez que
`boutique` soit prêt. Selon le moment où l'init container sera relancé, cela
peut prendre plus d'une minute :

```bash
kubectl wait --for=condition=Ready pod/boutique -n essai-init --timeout=300s; kubectl get pod boutique -n essai-init
```

```text
pod/boutique condition met
NAME       READY   STATUS    RESTARTS   AGE
boutique   1/1     Running   0          89s
```

La relance suivante a trouvé `stock-svc` qui répond, l'init container s'est
terminé et le conteneur principal a démarré. La colonne `RESTARTS` est
revenue à 0 : elle ne compte que les conteneurs principaux une fois le Pod
démarré. Les journaux de la dernière tentative :

```bash
kubectl logs boutique -n essai-init -c attendre-stock | tail -2
```

```text
stock-svc repond
```

## 📚 Exercice 5 : un init container qui échoue, avec relance

Comparez avec l'exercice 1. Créez un Pod `rate` dont l'init container sort
avec le code 1, sans `restartPolicy`, donc en `Always` :

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

Même `Init:Error` qu'à l'exercice 1, mais cette fois Kubernetes relance
l'init container (déjà 2 fois), et le Pod n'est pas en échec définitif. Un
init container doit **réussir** pour que le Pod démarre : c'est ce qui permet
de bloquer une application tant que sa dépendance manque.

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

À vous, seul cette fois : une application tourne déjà alors que sa
dépendance ne répond pas. Son gardien n'a rien retenu : trouvez pourquoi, et
réparez-le.

```bash
dsoxlab run ckad-init-container
dsoxlab challenge ckad-init-container
```
