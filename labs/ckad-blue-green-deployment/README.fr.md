# Basculer le trafic d'une version à l'autre

Un **Service** donne un nom et une adresse fixes à un groupe de Pods. Il ne
choisit pas ses Pods par leur nom, mais par leurs **labels** : c'est son
**sélecteur** (en anglais, *selector*). Changer ce sélecteur change les Pods
qui reçoivent le trafic. C'est tout le principe d'une livraison
**blue-green** : deux versions tournent en même temps, et le Service décide
laquelle répond. La leçon montre la bascule. Ce cours mesure ce qui se passe
pendant les secondes qui la suivent, et ce qui arrive quand on bascule vers une
version qui n'est pas prête.

Vous travaillez dans un namespace d'essai, `essai-bascule`, avec une
application `boutique` en plusieurs versions. Le challenge vous demandera le
même travail sur une autre application : vous le ferez seul, à la fin.

Page associée : [Services Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-blue-green-deployment
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : faire tourner deux versions en même temps

Chaque version est un Deployment de deux Pods. Leur conteneur écrit le nom de
sa version dans une page web, puis la sert avec le petit serveur `httpd` de
busybox, sur le port 8080. Une **sonde de disponibilité** (readinessProbe)
vérifie toutes les deux secondes que ce port répond : un Pod ne reçoit du
trafic que s'il est prêt. Les Pods portent deux labels : `app=boutique`,
commun à toutes les versions, et `version`, qui les distingue.

Créez le namespace d'essai, puis la `v1` :

```bash
kubectl create namespace essai-bascule
cat <<'YAML' | kubectl apply -n essai-bascule -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: boutique-v1
spec:
  replicas: 2
  selector:
    matchLabels:
      app: boutique
      version: v1
  template:
    metadata:
      labels:
        app: boutique
        version: v1
    spec:
      containers:
        - name: web
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "mkdir -p /www && echo v1 > /www/index.html && exec httpd -f -p 8080 -h /www"]
          ports:
            - containerPort: 8080
          readinessProbe:
            tcpSocket:
              port: 8080
            periodSeconds: 2
YAML
```

```text
namespace/essai-bascule created
deployment.apps/boutique-v1 created
```

Créez la `v2` avec le même manifeste, en remplaçant `v1` par `v2` aux quatre
endroits où il apparaît : le nom, les deux labels `version` et le texte servi.
Attendez ensuite les deux versions :

```bash
kubectl rollout status deployment/boutique-v1 -n essai-bascule --timeout=120s | tail -1
kubectl rollout status deployment/boutique-v2 -n essai-bascule --timeout=120s | tail -1
kubectl get pods -n essai-bascule -L version
```

```text
deployment "boutique-v1" successfully rolled out
deployment "boutique-v2" successfully rolled out
NAME                           READY   STATUS    RESTARTS   AGE   VERSION
boutique-v1-599bb57bc5-7m9zw   1/1     Running   0          1s    v1
boutique-v1-599bb57bc5-v8ttw   1/1     Running   0          1s    v1
boutique-v2-d57698b89-plf8q    1/1     Running   0          1s    v2
boutique-v2-d57698b89-xqcdw    1/1     Running   0          1s    v2
```

## 📚 Exercice 2 : un Service qui choisit les deux versions

Créez un Pod `sonde` pour interroger le Service de l'intérieur du cluster,
puis le Service `boutique`. Il écoute sur le port 80 et envoie vers le
port 8080 des Pods. Son sélecteur ne demande que `app=boutique` : il choisit
donc les Pods des deux versions.

```bash
kubectl run sonde \
  --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 \
  --restart=Never -n essai-bascule -- sleep 3600
cat <<'YAML' | kubectl apply -n essai-bascule -f -
apiVersion: v1
kind: Service
metadata:
  name: boutique
spec:
  selector:
    app: boutique
  ports:
    - port: 80
      targetPort: 8080
YAML
kubectl wait --for=condition=Ready pod/sonde -n essai-bascule --timeout=60s
```

```text
pod/sonde created
service/boutique created
pod/sonde condition met
```

Les adresses des Pods choisis par le Service s'appellent ses **endpoints**.
Rangez dans une variable la commande qui les affiche, avec l'état prêt ou non
de chacun, puis envoyez huit requêtes :

```bash
EP='{range .items[*].endpoints[*]}{.addresses[0]} pret={.conditions.ready}{"\n"}{end}'
kubectl get endpointslices -n essai-bascule -l kubernetes.io/service-name=boutique -o jsonpath="$EP"
for i in 1 2 3 4 5 6 7 8; do kubectl exec sonde -n essai-bascule -- wget -qO- -T 2 "http://boutique"; done
```

```text
10.244.38.100 pret=true
10.244.163.15 pret=true
10.244.38.96 pret=true
10.244.163.14 pret=true
v2
v1
v1
v1
v2
v1
v2
v2
```

Quatre endpoints prêts, et des réponses qui mélangent les deux versions. Le
port 80 n'apparaît pas dans l'adresse : c'est le port par défaut de HTTP.

## 📚 Exercice 3 : ne garder qu'une version

`kubectl set selector` remplace **tout** le sélecteur d'un Service. Donnez-lui
`version=v1` en plus d'`app=boutique` :

```bash
kubectl set selector service boutique 'app=boutique,version=v1' -n essai-bascule
kubectl get endpointslices -n essai-bascule -l kubernetes.io/service-name=boutique -o jsonpath="$EP"
for i in 1 2 3 4 5 6 7 8; do kubectl exec sonde -n essai-bascule -- wget -qO- -T 2 "http://boutique"; done
```

```text
service/boutique selector updated
10.244.38.100 pret=true
10.244.163.15 pret=true
v1
v1
v1
v1
v1
v1
v1
v1
```

Deux endpoints, et huit réponses `v1`. La `v2` tourne toujours, mais ne reçoit
plus rien.

## 📚 Exercice 4 : basculer, et mesurer les secondes qui suivent

La bascule ne change qu'une clé du sélecteur. `kubectl patch` modifie cette
seule clé et garde les autres, alors que `set selector` réécrit tout :

```bash
kubectl patch service boutique -n essai-bascule -p '{"spec":{"selector":{"version":"v2"}}}'
kubectl get service boutique -n essai-bascule -o jsonpath='{.spec.selector}{"\n"}'
kubectl get endpointslices -n essai-bascule -l kubernetes.io/service-name=boutique -o jsonpath="$EP"
for i in 1 2 3 4 5 6 7 8; do kubectl exec sonde -n essai-bascule -- wget -qO- -T 2 "http://boutique"; done
```

```text
service/boutique patched
{"app":"boutique","version":"v2"}
10.244.38.96 pret=true
10.244.163.14 pret=true
v1
v1
v1
v2
v2
v2
v2
v2
```

Le sélecteur garde `app=boutique`, et les endpoints sont déjà ceux de la `v2`.
Pourtant, les trois premières requêtes répondent encore `v1`. La liste des
endpoints change tout de suite dans l'API. Mais chaque nœud doit ensuite
appliquer cette liste à ses règles réseau, et cela prend quelques secondes.
Pendant ce temps, l'ancienne version reçoit encore du trafic : c'est une raison
de plus pour ne pas l'arrêter juste après la bascule. Les Pods des deux
versions tournent toujours :

```bash
kubectl get pods -n essai-bascule -l app=boutique -L version
```

```text
NAME                           READY   STATUS    RESTARTS   AGE   VERSION
boutique-v1-599bb57bc5-7m9zw   1/1     Running   0          5s    v1
boutique-v1-599bb57bc5-v8ttw   1/1     Running   0          5s    v1
boutique-v2-d57698b89-plf8q    1/1     Running   0          5s    v2
boutique-v2-d57698b89-xqcdw    1/1     Running   0          5s    v2
```

## 📚 Exercice 5 : le retour arrière

Revenir en arrière, c'est le même patch, avec l'ancienne valeur :

```bash
kubectl patch service boutique -n essai-bascule -p '{"spec":{"selector":{"version":"v1"}}}'
kubectl get endpointslices -n essai-bascule -l kubernetes.io/service-name=boutique -o jsonpath="$EP"
for i in 1 2 3 4 5 6 7 8; do kubectl exec sonde -n essai-bascule -- wget -qO- -T 2 "http://boutique"; done
```

```text
service/boutique patched
10.244.38.100 pret=true
10.244.163.15 pret=true
v2
v2
v2
v2
v2
v2
v2
v1
```

Même délai, dans l'autre sens : sept requêtes partent encore vers la `v2`,
puis la `v1` reprend la main. Le délai varie d'un essai à l'autre : vérifiez
une bascule quelques secondes après l'avoir faite, pas tout de suite.

## 📚 Exercice 6 : basculer vers une version qui n'est pas prête

Créez une `v3` qui démarre, mais dont la sonde de disponibilité vise le port
9999, où rien n'écoute. Reprenez le manifeste de la `v1`, avec `v3` aux quatre
mêmes endroits, et `port: 9999` dans `readinessProbe`. Après une quinzaine de
secondes, regardez-la **avant** de basculer :

```bash
kubectl get pods -n essai-bascule -l version=v3
kubectl get deployment boutique-v3 -n essai-bascule
```

```text
NAME                           READY   STATUS    RESTARTS   AGE
boutique-v3-5cf759fd9f-hs2f9   0/1     Running   0          15s
boutique-v3-5cf759fd9f-vpg78   0/1     Running   0          15s
NAME          READY   UP-TO-DATE   AVAILABLE   AGE
boutique-v3   0/2     2            0           15s
```

Les Pods tournent (`Running`), mais aucun n'est prêt (`0/1`), et le
Deployment n'a aucun Pod disponible. Basculez quand même, pour voir :

```bash
kubectl patch service boutique -n essai-bascule -p '{"spec":{"selector":{"version":"v3"}}}'
kubectl get endpointslices -n essai-bascule -l kubernetes.io/service-name=boutique -o jsonpath="$EP"
kubectl exec sonde -n essai-bascule -- wget -qO- -T 3 http://boutique
```

```text
service/boutique patched
10.244.38.93 pret=false
10.244.163.16 pret=false
wget: can't connect to remote host (10.109.37.21): Connection refused
command terminated with exit code 1
```

Le Service a bien trouvé les deux Pods de la `v3`, mais ils sont marqués
`pret=false`, et un Service n'envoie rien à un endpoint qui n'est pas prêt.
Toute l'application est coupée. Revenez à la `v1` :

```bash
kubectl patch service boutique -n essai-bascule -p '{"spec":{"selector":{"version":"v1"}}}'
kubectl get endpointslices -n essai-bascule -l kubernetes.io/service-name=boutique -o jsonpath="$EP"
kubectl exec sonde -n essai-bascule -- wget -qO- -T 3 http://boutique
```

```text
service/boutique patched
10.244.38.100 pret=true
10.244.163.15 pret=true
v1
```

Avant une bascule, vérifiez donc la cible : `READY` des Pods et `AVAILABLE`
du Deployment.

## 🧹 Nettoyage

Supprimez d'abord ce que vous avez créé pendant les exercices : le namespace
d'essai, avec tout ce qu'il contient.

```bash
kubectl delete namespace essai-bascule
```

```text
namespace "essai-bascule" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-blue-green-deployment
dsoxlab check ckad-blue-green-deployment
```

```text
╭─ Résultat : ckad-blue-green-deployment ─╮
│  0 / 100 pts                            │
│  ░░░░░░░░░░░░░░░░░░░░  0/10 tests       │
╰─────────────────────────────────────────╯
```

0 sur 10 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : faire tourner deux versions d'une application, puis
basculer son Service de l'une à l'autre, sans arrêter l'ancienne.

```bash
dsoxlab run ckad-blue-green-deployment
dsoxlab challenge ckad-blue-green-deployment
```
