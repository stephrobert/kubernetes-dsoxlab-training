# Exposer une application avec un Service

Les Pods d'une application changent d'adresse IP à chaque remplacement. Les
autres applications du cluster ne peuvent donc pas les joindre par leur
adresse. Un **Service** leur donne un **nom** et une **adresse fixes**, et
répartit les requêtes entre les Pods qu'il sélectionne. Dans ce cours, vous
créez un Service avec `kubectl expose`, vous le joignez par ses différents
noms, vous voyez ce qui se passe quand son port cible est faux, et quand un Pod
de trop entre dans sa sélection.

Vous travaillez dans un namespace d'essai, `essai-expose`, avec une application
`annuaire`. Le challenge vous demandera d'exposer une autre application : vous
le ferez seul, à la fin.

Page associée : [Services Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-expose-service
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : une application, sans Service

Créez le namespace d'essai :

```bash
kubectl create namespace essai-expose
```

```text
namespace/essai-expose created
```

L'application `annuaire` tourne en deux Pods. Leur conteneur sert le texte
`annuaire` sur le port 8080. Ce port a un **nom**, `http` : il servira à
l'exercice 5.

```bash
cat <<'YAML' | kubectl apply -n essai-expose -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: annuaire
spec:
  replicas: 2
  selector:
    matchLabels:
      app: annuaire
  template:
    metadata:
      labels:
        app: annuaire
    spec:
      containers:
        - name: web
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "echo annuaire > /tmp/index.html && httpd -f -p 8080 -h /tmp"]
          ports:
            - name: http
              containerPort: 8080
YAML
```

```text
deployment.apps/annuaire created
```

Attendez qu'elle soit prête, puis regardez ses Pods avec leur adresse (`-o
wide`) :

```bash
kubectl rollout status deployment/annuaire -n essai-expose --timeout=120s | tail -1
kubectl get pods -n essai-expose -o wide
```

```text
deployment "annuaire" successfully rolled out
NAME                       READY   STATUS    RESTARTS   AGE   IP              NODE         NOMINATED NODE   READINESS GATES
annuaire-78f54cb8c-6lddp   1/1     Running   0          1s    10.244.163.38   k8s-cp.lab   <none>           <none>
annuaire-78f54cb8c-bdsxp   1/1     Running   0          1s    10.244.38.106   k8s-w1.lab   <none>           <none>
```

Chaque Pod a sa propre adresse, sur un nœud différent. Ces adresses changent
dès qu'un Pod est remplacé. Pour interroger l'application de l'intérieur du
cluster, créez un Pod `sonde` qui ne fait que dormir :

```bash
kubectl run sonde --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --restart=Never -n essai-expose -- sleep 3600
kubectl wait --for=condition=Ready pod/sonde -n essai-expose --timeout=60s
```

```text
pod/sonde created
pod/sonde condition met
```

## 📚 Exercice 2 : créer le Service avec kubectl expose

`kubectl expose` crée un Service pour un Deployment, en reprenant son
sélecteur. Deux ports comptent :

- `--port` : le port du **Service**, celui que les autres applications
  appellent ;
- `--target-port` : le port des **conteneurs**, où le Service envoie les
  requêtes.

```bash
kubectl expose deployment annuaire --port=80 --target-port=8080 -n essai-expose
kubectl get service annuaire -n essai-expose
```

```text
service/annuaire exposed
NAME       TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
annuaire   ClusterIP   10.106.114.47   <none>        80/TCP    0s
```

Le Service est de type `ClusterIP` : il n'est joignable que depuis l'intérieur
du cluster, à l'adresse `10.106.114.47`, sur le port 80. `describe` montre le
reste (`grep` ne garde que les lignes utiles) :

```bash
kubectl describe service annuaire -n essai-expose | grep -E '^(Selector|Type|IP|Port|TargetPort|Endpoints):'
```

```text
Selector:                 app=annuaire
Type:                     ClusterIP
IP:                       10.106.114.47
Port:                     <unset>  80/TCP
TargetPort:               8080/TCP
Endpoints:                10.244.38.106:8080,10.244.163.38:8080
```

`Selector` dit quels Pods le Service choisit : ceux qui portent
`app=annuaire`. `Endpoints` liste leurs adresses, avec le port cible : ce sont
les deux Pods de l'exercice 1.

## 📚 Exercice 3 : joindre le Service par son nom

Le DNS du cluster donne un nom à chaque Service. Depuis un Pod du **même**
namespace, le nom court suffit :

```bash
kubectl exec sonde -n essai-expose -- wget -qO- -T 2 http://annuaire
```

```text
annuaire
```

Depuis un autre namespace, il faut ajouter le namespace, ou donner le nom
complet :

```bash
kubectl exec sonde -n essai-expose -- wget -qO- -T 2 http://annuaire.essai-expose
kubectl exec sonde -n essai-expose -- wget -qO- -T 2 http://annuaire.essai-expose.svc.cluster.local
```

```text
annuaire
annuaire
```

Le port 80 n'apparaît pas dans l'adresse : c'est le port par défaut de HTTP, et
c'est celui du Service. `nslookup` montre à quelle adresse le nom renvoie :

```bash
kubectl exec sonde -n essai-expose -- nslookup annuaire.essai-expose.svc.cluster.local
```

```text
Server:		10.96.0.10
Address:	10.96.0.10:53


Name:	annuaire.essai-expose.svc.cluster.local
Address: 10.106.114.47
```

Le nom renvoie à l'adresse fixe du Service (`10.106.114.47`), jamais à celle
d'un Pod.

## 📚 Exercice 4 : un port cible qui ne mène nulle part

Créez un second Service, avec un port cible faux, `9090`, alors que les
conteneurs écoutent sur 8080 :

```bash
kubectl expose deployment annuaire --name=annuaire-faux --port=80 --target-port=9090 -n essai-expose
kubectl get endpointslices -n essai-expose -l kubernetes.io/service-name=annuaire-faux
```

```text
service/annuaire-faux exposed
NAME                  ADDRESSTYPE   PORTS   ENDPOINTS                     AGE
annuaire-faux-bfnzx   IPv4          9090    10.244.163.38,10.244.38.106   0s
```

Les endpoints sont là, mais sur le port `9090`. Le sélecteur est bon, donc
Kubernetes a bien trouvé les Pods. Rien ne vérifie pourtant qu'ils écoutent sur
ce port :

```bash
kubectl exec sonde -n essai-expose -- wget -qO- -T 3 http://annuaire-faux
```

```text
wget: download timed out
command terminated with exit code 1
```

La requête n'aboutit pas. Retenez la différence : **pas d'endpoint**, c'est le
sélecteur qui est faux. **Des endpoints, mais pas de réponse**, c'est souvent
le port cible. Supprimez ce Service :

```bash
kubectl delete service annuaire-faux -n essai-expose
```

```text
service "annuaire-faux" deleted from essai-expose namespace
```

## 📚 Exercice 5 : viser un port par son nom

Le port du conteneur s'appelle `http` :

```bash
kubectl get deployment annuaire -n essai-expose -o jsonpath='{.spec.template.spec.containers[0].ports[0]}{"\n"}'
```

```text
{"containerPort":8080,"name":"http","protocol":"TCP"}
```

Le port cible d'un Service peut donner ce nom au lieu du numéro :

```bash
kubectl expose deployment annuaire --name=annuaire-nomme --port=80 --target-port=http -n essai-expose
kubectl get service annuaire-nomme -n essai-expose -o jsonpath='{.spec.ports[0].targetPort}{"\n"}'
sleep 2; kubectl exec sonde -n essai-expose -- wget -qO- -T 2 http://annuaire-nomme
```

```text
service/annuaire-nomme exposed
http
annuaire
```

L'intérêt : si l'application change un jour de port, il suffit de modifier le
Deployment. Le Service, qui vise `http`, suit sans retouche.

## 📚 Exercice 6 : un Pod de trop dans le Service

Le Service `annuaire` a deux endpoints, les deux Pods de l'application :

```bash
kubectl get endpointslices -n essai-expose -l kubernetes.io/service-name=annuaire
```

```text
NAME             ADDRESSTYPE   PORTS   ENDPOINTS                     AGE
annuaire-lr9v8   IPv4          8080    10.244.38.106,10.244.163.38   7s
```

Le Service choisit **tous** les Pods du namespace qui portent `app=annuaire`,
même ceux qui ne font pas partie de l'application. Donnez ce label à la sonde :

```bash
kubectl label pod sonde app=annuaire -n essai-expose
sleep 3; kubectl get endpointslices -n essai-expose -l kubernetes.io/service-name=annuaire
```

```text
pod/sonde labeled
NAME             ADDRESSTYPE   PORTS   ENDPOINTS                                   AGE
annuaire-lr9v8   IPv4          8080    10.244.38.106,10.244.163.38,10.244.38.107   10s
```

La sonde est devenue un troisième endpoint. Or elle ne sert rien sur le
port 8080. Envoyez six requêtes (`|| echo ECHEC` signale chaque requête
ratée) :

```bash
for i in 1 2 3 4 5 6; do kubectl exec sonde -n essai-expose -- wget -qO- -T 2 'http://annuaire' || echo ECHEC; done
```

```text
annuaire
wget: can't connect to remote host (10.106.114.47): Connection refused
command terminated with exit code 1
ECHEC
annuaire
annuaire
annuaire
annuaire
```

Une requête a échoué : celle que le Service a envoyée à la sonde. Le partage se
fait au hasard, donc vous pouvez en voir plus ou moins. Retirez le label (le
tiret après la clé l'efface), puis recommencez :

```bash
kubectl label pod sonde app- -n essai-expose
sleep 3; for i in 1 2 3 4 5 6; do kubectl exec sonde -n essai-expose -- wget -qO- -T 2 'http://annuaire' || echo ECHEC; done
```

```text
pod/sonde unlabeled
annuaire
annuaire
annuaire
annuaire
annuaire
annuaire
```

Six réponses sur six. Avant de conclure qu'un Service marche, comptez ses
endpoints : il doit y en avoir autant que de Pods de l'application.

## 🧹 Nettoyage

Supprimez le namespace d'essai, avec tout ce qu'il contient :

```bash
kubectl delete namespace essai-expose
```

```text
namespace "essai-expose" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-expose-service
dsoxlab check ckad-expose-service
```

```text
╭── Résultat : ckad-expose-service ──╮
│  0 / 100 pts                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/11 tests  │
╰────────────────────────────────────╯
```

0 sur 11 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un serveur web en trois exemplaires, chacun
répondant son propre nom, joignable par les autres applications sous un nom
stable.

```bash
dsoxlab run ckad-expose-service
dsoxlab challenge ckad-expose-service
```
