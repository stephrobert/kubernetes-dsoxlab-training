# Atteindre une application depuis la machine

Une application qui tourne dans le cluster n'est pas joignable directement
depuis votre machine : les adresses des Pods et des Services n'existent qu'à
l'intérieur du cluster. Pour l'essayer quand même, kubectl ouvre des
**tunnels** : `kubectl port-forward` relie un port de votre machine à un Pod ou
à un Service, et `kubectl proxy` ouvre un accès à l'API du cluster. Dans ce
cours, vous créez un Service en regardant d'abord ce qu'il contiendra, vous
ouvrez des tunnels vers un Pod puis vers un Service, et vous passez par l'API.

Vous travaillez dans un namespace d'essai, `essai-acces`, avec une application
`miroir`. Le challenge vous demandera le même travail sur une autre
application : vous le ferez seul, à la fin.

Page associée : [kubectl expose, port-forward et proxy](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-expose-port-forward-proxy/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-atteindre-une-application
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`boutique` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026.

## 📚 Exercice 1 : une application sans Service

Créez le namespace d'essai et l'application `miroir` : deux Pods agnhost, un
petit serveur de test, qui écoutent sur le port 8080. Sur le chemin
`/hostname`, chaque Pod répond son propre nom.

```bash
kubectl create namespace essai-acces
kubectl create deployment miroir --image=registry.k8s.io/e2e-test-images/agnhost:2.61@sha256:101f3357d1ad890c3090e78ea6c6a47dc5137cbe19836796e13d5dcb2b84d2e6 --replicas=2 -n essai-acces -- /agnhost netexec --http-port=8080
kubectl rollout status deployment/miroir -n essai-acces --timeout=180s | tail -1
kubectl get pods -n essai-acces
```

```text
namespace/essai-acces created
deployment.apps/miroir created
deployment "miroir" successfully rolled out
NAME                      READY   STATUS    RESTARTS   AGE
miroir-67cbf77d75-8xqv7   1/1     Running   0          1s
miroir-67cbf77d75-dknsx   1/1     Running   0          1s
```

## 📚 Exercice 2 : regarder un Service avant de le créer

`kubectl expose` crée un Service à votre place, et choisit plusieurs valeurs
sans vous le dire. `--dry-run=client -o yaml` montre le manifeste qu'il
écrirait, **sans rien créer** :

```bash
kubectl expose deployment miroir --port=80 -n essai-acces --dry-run=client -o yaml
```

```text
apiVersion: v1
kind: Service
metadata:
  labels:
    app: miroir
  name: miroir
  namespace: essai-acces
spec:
  ports:
  - port: 80
    protocol: TCP
    targetPort: 80
  selector:
    app: miroir
status:
  loadBalancer: {}
```

Deux choses à lire :

- `selector: app: miroir` : il a repris le sélecteur du Deployment ;
- `targetPort: 80` : sans `--target-port`, il reprend la valeur de `--port`. Or
  les Pods écoutent sur 8080 : ce Service n'aurait rien trouvé.

Créez le vrai Service, avec le bon port cible, puis vérifiez qu'il a trouvé les
deux Pods :

```bash
kubectl expose deployment miroir --port=80 --target-port=8080 -n essai-acces
kubectl get endpointslices -n essai-acces -l kubernetes.io/service-name=miroir
```

```text
service/miroir exposed
NAME           ADDRESSTYPE   PORTS   ENDPOINTS               AGE
miroir-pg69k   IPv4          8080    10.244.0.8,10.244.0.7   0s
```

## 📚 Exercice 3 : un tunnel vers un Pod

`kubectl port-forward` relie un port de votre machine à un port du cluster. Il
tourne tant que la commande tourne : lancez-le en arrière-plan (le `&` final),
avec ses messages dans un journal. Les ports se lisent « local, puis
distant » : `19090:8080` relie le port 19090 de la machine au port 8080 du Pod.

```bash
POD=$(kubectl get pods -n essai-acces -o jsonpath='{.items[0].metadata.name}')
echo $POD
kubectl port-forward pod/$POD 19090:8080 -n essai-acces > /tmp/tunnel-pod.log 2>&1 &
```

```text
miroir-67cbf77d75-8xqv7
```

Le shell affiche aussi une ligne `[1]` suivie d'un numéro de processus : c'est
le numéro de la tâche en arrière-plan. Interrogez maintenant le port local
(le `echo` ajoute le retour à la ligne que la réponse n'a pas), puis lisez le
journal du tunnel :

```bash
curl -s 'http://127.0.0.1:19090/hostname'; echo
cat /tmp/tunnel-pod.log
```

```text
miroir-67cbf77d75-8xqv7
Forwarding from 127.0.0.1:19090 -> 8080
Forwarding from [::1]:19090 -> 8080
Handling connection for 19090
```

Le Pod répond à travers le tunnel. Le journal dit où mène le tunnel, puis une
ligne `Handling connection` par requête. Fermez-le en tuant la tâche numéro 1 :

```bash
kill %1
```

Le shell confirme d'une ligne `Terminated`.

## 📚 Exercice 4 : un tunnel vers le Service

Un tunnel peut aussi viser le Service. Ouvrez-le sur le port local 19091, puis
envoyez quatre requêtes :

```bash
kubectl port-forward service/miroir 19091:80 -n essai-acces > /tmp/tunnel-svc.log 2>&1 &
for i in 1 2 3 4; do curl -s 'http://127.0.0.1:19091/hostname'; echo; done
cat /tmp/tunnel-svc.log
```

```text
miroir-67cbf77d75-8xqv7
miroir-67cbf77d75-8xqv7
miroir-67cbf77d75-8xqv7
miroir-67cbf77d75-8xqv7
Forwarding from 127.0.0.1:19091 -> 8080
Forwarding from [::1]:19091 -> 8080
Handling connection for 19091
Handling connection for 19091
Handling connection for 19091
Handling connection for 19091
```

Quatre fois le même Pod. Un tunnel vers un Service ne répartit **pas** les
requêtes : au lancement, kubectl choisit **un** Pod du Service, et tout le
tunnel mène à lui. Le journal le confirme : `-> 8080`, le port du Pod, et non
80, celui du Service. Fermez ce tunnel :

```bash
kill %1
```

## 📚 Exercice 5 : le tunnel meurt avec son processus

Ouvrez un tunnel, vérifiez qu'il répond, fermez-le, puis interrogez-le de
nouveau :

```bash
kubectl port-forward service/miroir 19092:80 -n essai-acces > /tmp/tunnel-2.log 2>&1 &
curl -s 'http://127.0.0.1:19092/hostname'; echo
kill %1
curl -s -m 2 http://127.0.0.1:19092/hostname || echo "plus rien sur 19092 (code $?)"
```

```text
miroir-67cbf77d75-8xqv7
plus rien sur 19092 (code 7)
```

Un tunnel n'est pas un objet du cluster, comme un Service : c'est un
**processus** sur votre machine. Le processus tué, le port local ne mène plus
nulle part (`curl` sort en code 7, connexion refusée). Si vous fermez votre
session SSH, vos tunnels s'arrêtent avec elle.

## 📚 Exercice 6 : un port local déjà pris

Un port local ne sert qu'à un tunnel à la fois. Ouvrez-en un sur 19093, puis
essayez d'en ouvrir un second sur le même port, au premier plan cette fois :

```bash
kubectl port-forward service/miroir 19093:80 -n essai-acces > /tmp/tunnel-a.log 2>&1 &
kubectl port-forward service/miroir 19093:80 -n essai-acces; echo "code du second tunnel : $?"
```

```text
Unable to listen on port 19093: Listeners failed to create with the following errors: [unable to create listener: Error listen tcp4 127.0.0.1:19093: bind: address already in use unable to create listener: Error listen tcp6 [::1]:19093: bind: address already in use]
error: unable to listen on any of the requested ports: [{19093 8080}]
code du second tunnel : 1
```

Refusé : `address already in use`. Si un tunnel refuse de démarrer, cherchez
d'abord un ancien tunnel resté ouvert sur le même port. Fermez le premier :

```bash
kill %1
```

## 📚 Exercice 7 : passer par l'API avec kubectl proxy

`kubectl proxy` ouvre un accès local à l'**API du cluster**, avec vos droits
kubectl. Par l'API, on atteint aussi un Service, à une adresse longue mais
régulière :
`/api/v1/namespaces/<namespace>/services/<service>:<port>/proxy/<chemin>`.

```bash
kubectl proxy --port=8001 > /tmp/proxy.log 2>&1 &
cat /tmp/proxy.log
curl -s 'http://127.0.0.1:8001/api/v1/namespaces/essai-acces/services/miroir:80/proxy/hostname'; echo
kill %1
```

```text
Starting to serve on 127.0.0.1:8001
miroir-67cbf77d75-8xqv7
```

La requête est passée par l'API, puis par le Service, jusqu'à un Pod. À la
différence de `port-forward`, un seul proxy donne accès à tous les Services du
cluster.

## 🧹 Nettoyage

Supprimez le namespace d'essai, avec tout ce qu'il contient :

```bash
kubectl delete namespace essai-acces
```

```text
namespace "essai-acces" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-atteindre-une-application
dsoxlab check k8s-atteindre-une-application
```

```text
╭─ Résultat : k8s-atteindre-une-application ─╮
│  0 / 100 pts                               │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests           │
╰────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : exposer une application par un Service, puis ouvrir
un tunnel vers lui et noter le Pod qui vous répond.

```bash
dsoxlab run k8s-atteindre-une-application
dsoxlab challenge k8s-atteindre-une-application
```
