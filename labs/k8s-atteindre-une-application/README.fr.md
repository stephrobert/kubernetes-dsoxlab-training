# Atteindre une application depuis la machine

Une application qui tourne dans le cluster n'est pas joignable directement
depuis votre machine : les adresses des Pods et des Services n'existent qu'à
l'intérieur du cluster. Pour l'essayer quand même, kubectl ouvre des
**tunnels** : `kubectl port-forward` relie un port de votre machine à un Pod ou
à un Service, et `kubectl proxy` ouvre un accès à l'API du cluster. La leçon
montre ces trois commandes quand tout marche. Ce cours vous fait lire leurs
messages quand quelque chose cloche : un Service au mauvais port cible, un
port local déjà pris, un Service sans Pod.

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
20 novembre 2026.

## 📚 Exercice 1 : une application sans Service

Créez le namespace d'essai et l'application `miroir` : deux Pods agnhost, un
petit serveur de test, qui écoutent sur le port 9090. Sur le chemin
`/hostname`, chaque Pod répond son propre nom.

```bash
kubectl create namespace essai-acces
kubectl create deployment miroir \
  --image=registry.k8s.io/e2e-test-images/agnhost:2.61@sha256:101f3357d1ad890c3090e78ea6c6a47dc5137cbe19836796e13d5dcb2b84d2e6 \
  --replicas=2 -n essai-acces -- /agnhost netexec --http-port=9090
kubectl rollout status deployment/miroir -n essai-acces --timeout=180s | tail -1
kubectl get pods -n essai-acces
```

```text
namespace/essai-acces created
deployment.apps/miroir created
deployment "miroir" successfully rolled out
NAME                      READY   STATUS    RESTARTS   AGE
miroir-78b9b787d7-jbxhr   1/1     Running   0          1s
miroir-78b9b787d7-jht9z   1/1     Running   0          1s
```

## 📚 Exercice 2 : un tunnel vers un Service au mauvais port

`kubectl expose` choisit des valeurs sans vous le dire. `--dry-run=client -o
yaml` montre le manifeste qu'il écrirait, sans rien créer :

```bash
kubectl expose deployment miroir --port=80 -n essai-acces --dry-run=client -o yaml
```

```text title="Extrait de la sortie"
spec:
  ports:
  - port: 80
    protocol: TCP
    targetPort: 80
  selector:
    app: miroir
```

Sans `--target-port`, il reprend la valeur de `--port` : `targetPort: 80`. Or
les Pods écoutent sur 9090. Créez ce Service fautif pour de bon, et regardez ce
qu'il a trouvé :

```bash
kubectl expose deployment miroir --port=80 -n essai-acces
kubectl get endpointslices -n essai-acces -l kubernetes.io/service-name=miroir
```

```text
service/miroir exposed
NAME           ADDRESSTYPE   PORTS   ENDPOINTS                 AGE
miroir-nhpgp   IPv4          80      10.244.0.20,10.244.0.21   0s
```

Les deux Pods sont là : le sélecteur est bon. La colonne `PORTS` dit `80`, le
port où le Service enverra les requêtes. Ouvrez un tunnel vers ce Service.
`kubectl port-forward` tourne tant que la commande tourne : lancez-le en
arrière-plan (le `&` final), avec ses messages dans un journal, et laissez-lui
deux secondes pour s'ouvrir. Les ports se lisent « local, puis distant » :
`19090:80` relie le port 19090 de la machine au port 80 du Service.

```bash
kubectl port-forward service/miroir 19090:80 -n essai-acces > /tmp/tunnel-faux.log 2>&1 &
sleep 2
curl -s -m 3 "http://127.0.0.1:19090/hostname"; echo "code curl : $?"
cat /tmp/tunnel-faux.log
```

```text
code curl : 52
Forwarding from 127.0.0.1:19090 -> 80
Forwarding from [::1]:19090 -> 80
Handling connection for 19090
E1120 11:59:54.701770   14943 portforward.go:549] "An error occurred forwarding" err="error forwarding port 80 to pod 195d9c4f5fccf6ab1cd97c7a7ecf76e2471a519cf3bb60070716019321468575, uid : failed to execute portforward in network namespace \"/var/run/netns/cni-be65d530-395b-d828-cc7d-20007401e83d\": failed to connect to localhost:80 inside namespace \"195d9c4f5fccf6ab1cd97c7a7ecf76e2471a519cf3bb60070716019321468575\", IPv4: dial tcp4 127.0.0.1:80: connect: connection refused IPv6 dial tcp6 [::1]:80: connect: connection refused " localPort=19090 remotePort=80
error: lost connection to pod
```

`curl` sort en code 52 : la connexion s'est ouverte, puis fermée sans réponse.
Le journal dit pourquoi : `failed to connect to localhost:80 inside namespace
... connection refused`. Le tunnel est arrivé dans le Pod, sur le port 80, et
rien n'y écoute. La dernière ligne, `lost connection to pod`, dit que le
tunnel s'est arrêté de lui-même. Remplacez le Service par un Service au bon
port cible :

```bash
kubectl delete service miroir -n essai-acces
kubectl expose deployment miroir --port=80 --target-port=9090 -n essai-acces
kubectl get endpointslices -n essai-acces -l kubernetes.io/service-name=miroir
```

```text
service "miroir" deleted from essai-acces namespace
service/miroir exposed
NAME           ADDRESSTYPE   PORTS   ENDPOINTS                 AGE
miroir-w6svj   IPv4          9090    10.244.0.20,10.244.0.21   0s
```

La colonne `PORTS` dit maintenant `9090`, le port où les Pods écoutent.

## 📚 Exercice 3 : un tunnel vers le Service ne répartit pas

Ouvrez un tunnel vers le Service corrigé, sur le port local 19091, puis
envoyez quatre requêtes. Le `echo` ajoute le retour à la ligne que la réponse
n'a pas :

```bash
kubectl port-forward service/miroir 19091:80 -n essai-acces > /tmp/tunnel-svc.log 2>&1 &
sleep 2
for i in 1 2 3 4; do curl -s "http://127.0.0.1:19091/hostname"; echo; done
cat /tmp/tunnel-svc.log
```

```text
miroir-78b9b787d7-jbxhr
miroir-78b9b787d7-jbxhr
miroir-78b9b787d7-jbxhr
miroir-78b9b787d7-jbxhr
Forwarding from 127.0.0.1:19091 -> 9090
Forwarding from [::1]:19091 -> 9090
Handling connection for 19091
Handling connection for 19091
Handling connection for 19091
Handling connection for 19091
```

Quatre fois le même Pod. Un tunnel vers un Service ne répartit **pas** les
requêtes : au lancement, kubectl choisit **un** Pod du Service, et tout le
tunnel mène à lui. Le journal le confirme : `-> 9090`, le port du Pod, et non
80, celui du Service. Fermez ce tunnel en tuant la tâche numéro 1 :

```bash
kill %1
```

## 📚 Exercice 4 : le tunnel meurt avec son processus

Ouvrez un tunnel, vérifiez qu'il répond, fermez-le, puis interrogez-le de
nouveau :

```bash
kubectl port-forward service/miroir 19092:80 -n essai-acces > /tmp/tunnel-2.log 2>&1 &
sleep 2
curl -s "http://127.0.0.1:19092/hostname"; echo
kill %1
sleep 1
curl -s -m 2 http://127.0.0.1:19092/hostname || echo "plus rien sur 19092 (code $?)"
```

```text
miroir-78b9b787d7-jbxhr
plus rien sur 19092 (code 7)
```

Un tunnel n'est pas un objet du cluster, comme un Service : c'est un
**processus** sur votre machine. Le processus tué, le port local ne mène plus
nulle part (`curl` sort en code 7, connexion refusée). Si vous fermez votre
session SSH, vos tunnels s'arrêtent avec elle.

## 📚 Exercice 5 : un port local déjà pris

Un port local ne sert qu'à un tunnel à la fois. Ouvrez-en un sur 19093, puis
essayez d'en ouvrir un second sur le même port, au premier plan cette fois :

```bash
kubectl port-forward service/miroir 19093:80 -n essai-acces > /tmp/tunnel-a.log 2>&1 &
sleep 2
kubectl port-forward service/miroir 19093:80 -n essai-acces; echo "code du second tunnel : $?"
```

```text
Unable to listen on port 19093: Listeners failed to create with the following errors: [unable to create listener: Error listen tcp4 127.0.0.1:19093: bind: address already in use unable to create listener: Error listen tcp6 [::1]:19093: bind: address already in use]
error: unable to listen on any of the requested ports: [{19093 9090}]
code du second tunnel : 1
```

Refusé : `address already in use`. Sans le `sleep 2`, le second tunnel
pourrait démarrer avant le premier et prendre le port à sa place. Si un tunnel
refuse de démarrer, cherchez d'abord un ancien tunnel resté ouvert sur le même
port. Fermez le premier :

```bash
kill %1
```

## 📚 Exercice 6 : passer par l'API avec kubectl proxy

`kubectl proxy` ouvre un accès local à l'**API du cluster**, avec vos droits
kubectl. Par l'API, on atteint aussi un Service, à une adresse longue mais
régulière :
`/api/v1/namespaces/<namespace>/services/<service>:<port>/proxy/<chemin>`.
Lancez le proxy, puis interrogez `miroir` deux fois : avec un chemin, puis sans
rien après `proxy`. L'option `-w` de `curl` affiche le code HTTP et l'adresse
de redirection :

```bash
kubectl proxy --port=8001 > /tmp/proxy.log 2>&1 &
sleep 2
cat /tmp/proxy.log
curl -s "http://127.0.0.1:8001/api/v1/namespaces/essai-acces/services/miroir:80/proxy/hostname"; echo
curl -s -o /dev/null -w "%{http_code} %{redirect_url}\n" http://127.0.0.1:8001/api/v1/namespaces/essai-acces/services/miroir:80/proxy
```

```text
Starting to serve on 127.0.0.1:8001
miroir-78b9b787d7-jbxhr
301 http://127.0.0.1:8001/api/v1/namespaces/essai-acces/services/miroir:80/proxy/
```

La première requête passe par l'API, puis par le Service, jusqu'à un Pod. La
seconde reçoit un code `301` : l'API renvoie vers la même adresse terminée par
une barre oblique. Un navigateur suit ce renvoi tout seul, `curl` non.

Passez maintenant `miroir` à zéro Pod, attendez que les Pods disparaissent,
puis interrogez de nouveau :

```bash
kubectl scale deployment miroir --replicas=0 -n essai-acces
kubectl wait --for=delete pod -l app=miroir -n essai-acces --timeout=60s
curl -s -w "\ncode HTTP %{http_code}\n" http://127.0.0.1:8001/api/v1/namespaces/essai-acces/services/miroir:80/proxy/hostname
```

```text title="Extrait de la sortie"
{
  "kind": "Status",
  "apiVersion": "v1",
  "metadata": {},
  "status": "Failure",
  "message": "no endpoints available for service \"miroir\"",
  "reason": "ServiceUnavailable",
  "code": 503
}
code HTTP 503
```

Par l'API, la panne est dite en clair : `no endpoints available`, avec le code
503. Remettez deux Pods, vérifiez que le Service répond de nouveau, puis
fermez le proxy :

```bash
kubectl scale deployment miroir --replicas=2 -n essai-acces
kubectl rollout status deployment/miroir -n essai-acces --timeout=120s | tail -1
sleep 2
curl -s "http://127.0.0.1:8001/api/v1/namespaces/essai-acces/services/miroir:80/proxy/hostname"; echo
kill %1
```

```text title="Extrait de la sortie"
deployment "miroir" successfully rolled out
miroir-78b9b787d7-dxbt8
```

À la différence de `port-forward`, un seul proxy donne accès à tous les
Services du cluster.

## 🧹 Nettoyage

Supprimez d'abord ce que vous avez créé pendant les exercices : le namespace
d'essai, avec tout ce qu'il contient, et les journaux des tunnels.

```bash
kubectl delete namespace essai-acces
rm -f /tmp/tunnel-*.log /tmp/proxy.log
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
