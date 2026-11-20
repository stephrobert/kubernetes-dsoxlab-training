# Exposer une application avec un Service

Les Pods d'une application changent d'adresse IP à chaque remplacement. Les
autres applications du cluster ne peuvent donc pas les joindre par leur
adresse. Un **Service** leur donne un **nom** et une **adresse fixes**, et
répartit les requêtes entre les Pods qu'il sélectionne. La leçon crée un
Service avec `kubectl expose` et le joint par son nom. Ce cours vous fait
écrire un Service à la main, distinguer deux Services du même nom dans deux
namespaces, et reconnaître deux pannes : un port cible faux, et un Pod de trop
dans la sélection.

Vous travaillez dans deux namespaces d'essai, `essai-expose` et
`essai-voisin`, avec une application `annuaire`. Le challenge vous demandera
d'exposer une autre application : vous le ferez seul, à la fin.

Page associée : [Services Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-expose-service
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : une application, sans Service

Créez le namespace d'essai, puis l'application `annuaire`, en deux Pods. Leur
conteneur sert le texte `annuaire` sur le port 8080. Ce port a un **nom**,
`http` : il servira à l'exercice 5.

```bash
kubectl create namespace essai-expose
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
          command: ["sh", "-c", "mkdir -p /www && echo annuaire > /www/index.html && exec httpd -f -p 8080 -h /www"]
          ports:
            - name: http
              containerPort: 8080
YAML
```

```text
namespace/essai-expose created
deployment.apps/annuaire created
```

Attendez qu'elle soit prête, puis regardez ses Pods avec leur adresse :

```bash
kubectl rollout status deployment/annuaire -n essai-expose --timeout=120s | tail -1
kubectl get pods -n essai-expose -o wide
```

```text
deployment "annuaire" successfully rolled out
NAME                       READY   STATUS    RESTARTS   AGE   IP              NODE         NOMINATED NODE   READINESS GATES
annuaire-59d6c5c5d-t5h74   1/1     Running   0          1s    10.244.38.91    k8s-w1.lab   <none>           <none>
annuaire-59d6c5c5d-xg58z   1/1     Running   0          1s    10.244.163.12   k8s-cp.lab   <none>           <none>
```

Chaque Pod a sa propre adresse, sur un nœud différent. Pour interroger
l'application de l'intérieur du cluster, créez un Pod `sonde` qui ne fait que
dormir :

```bash
kubectl run sonde \
  --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 \
  --restart=Never -n essai-expose -- sleep 3600
kubectl wait --for=condition=Ready pod/sonde -n essai-expose --timeout=60s
```

```text
pod/sonde created
pod/sonde condition met
```

## 📚 Exercice 2 : écrire le Service à la main

La leçon crée son Service avec `kubectl expose`. Écrivez celui-ci dans un
fichier : vous voyez ainsi les trois champs qui comptent.

```bash
cat > ~/essai-annuaire-svc.yaml <<'YAML'
apiVersion: v1
kind: Service
metadata:
  name: annuaire
  namespace: essai-expose
spec:
  selector:
    app: annuaire
  ports:
    - port: 80
      targetPort: 8080
YAML
kubectl apply -f ~/essai-annuaire-svc.yaml
kubectl get service annuaire -n essai-expose
kubectl get endpointslices -n essai-expose -l kubernetes.io/service-name=annuaire
```

```text
service/annuaire created
NAME       TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
annuaire   ClusterIP   10.110.40.62   <none>        80/TCP    0s
NAME             ADDRESSTYPE   PORTS   ENDPOINTS                    AGE
annuaire-lrgrj   IPv4          8080    10.244.163.12,10.244.38.91   0s
```

`selector` dit quels Pods le Service choisit : ceux qui portent
`app=annuaire`. `port` est le port du Service, celui qu'on appelle. `targetPort`
est le port des conteneurs, où il envoie les requêtes. Sans `type`, le Service
est un `ClusterIP` : joignable seulement de l'intérieur du cluster. Les deux
adresses des endpoints sont celles des Pods de l'exercice 1. Interrogez-le par
son nom :

```bash
kubectl exec sonde -n essai-expose -- wget -qO- -T 2 http://annuaire
```

```text
annuaire
```

## 📚 Exercice 3 : deux Services du même nom

Un nom de Service n'est unique qu'à l'intérieur de son namespace. Créez un
second namespace, avec une application `annuaire` qui sert `voisin`, et le
même Service :

```bash
kubectl create namespace essai-voisin
cat <<'YAML' | kubectl apply -n essai-voisin -f -
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
          command: ["sh", "-c", "mkdir -p /www && echo voisin > /www/index.html && exec httpd -f -p 8080 -h /www"]
          ports:
            - name: http
              containerPort: 8080
YAML
sed "s/namespace: essai-expose/namespace: essai-voisin/" ~/essai-annuaire-svc.yaml | kubectl apply -f -
kubectl rollout status deployment/annuaire -n essai-voisin --timeout=120s | tail -1
kubectl get services -A --field-selector metadata.name=annuaire
```

```text title="Extrait de la sortie"
namespace/essai-voisin created
deployment.apps/annuaire created
service/annuaire created
deployment "annuaire" successfully rolled out
NAMESPACE      NAME       TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
essai-expose   annuaire   ClusterIP   10.110.40.62    <none>        80/TCP    7s
essai-voisin   annuaire   ClusterIP   10.100.94.251   <none>        80/TCP    4s
```

Deux Services `annuaire`, deux adresses. Depuis la sonde, interrogez le nom
court, puis le nom suivi du namespace :

```bash
kubectl exec sonde -n essai-expose -- wget -qO- -T 2 http://annuaire
kubectl exec sonde -n essai-expose -- wget -qO- -T 2 http://annuaire.essai-voisin
```

```text
annuaire
voisin
```

Le nom court mène au Service du namespace de la sonde. Pour atteindre l'autre,
il faut ajouter son namespace. La raison se lit dans la configuration DNS du
Pod :

```bash
kubectl exec sonde -n essai-expose -- cat /etc/resolv.conf
```

```text
search essai-expose.svc.cluster.local svc.cluster.local cluster.local lab
nameserver 10.96.0.10
options ndots:5
```

La ligne `search` liste les suffixes essayés dans l'ordre. `annuaire` devient
d'abord `annuaire.essai-expose.svc.cluster.local` : le namespace du Pod passe
en premier. `annuaire.essai-voisin` devient
`annuaire.essai-voisin.svc.cluster.local` avec le deuxième suffixe.

## 📚 Exercice 4 : un port cible qui ne mène nulle part

Créez un troisième Service, avec un port cible faux, `9090`, alors que les
conteneurs écoutent sur 8080. Attendez quelques secondes que le Service soit
en place, puis interrogez-le :

```bash
kubectl expose deployment annuaire --name=annuaire-faux --port=80 --target-port=9090 -n essai-expose
kubectl get endpointslices -n essai-expose -l kubernetes.io/service-name=annuaire-faux
sleep 3
kubectl exec sonde -n essai-expose -- wget -qO- -T 3 http://annuaire-faux
```

```text
service/annuaire-faux exposed
NAME                  ADDRESSTYPE   PORTS   ENDPOINTS                    AGE
annuaire-faux-jffnm   IPv4          9090    10.244.163.12,10.244.38.91   0s
wget: can't connect to remote host (10.98.214.179): Connection refused
command terminated with exit code 1
```

Les endpoints sont là, sur le port `9090` : le sélecteur est bon, Kubernetes a
trouvé les Pods. Rien ne vérifie pourtant qu'ils écoutent sur ce port.
`Connection refused` veut dire que la requête est arrivée au Pod, et que rien
n'y écoute sur ce port. Retenez la différence : **pas d'endpoint**, c'est le
sélecteur qui est faux ; **des endpoints, et une connexion refusée**, c'est
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
sleep 3; kubectl exec sonde -n essai-expose -- wget -qO- -T 2 http://annuaire-nomme
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
NAME             ADDRESSTYPE   PORTS   ENDPOINTS                    AGE
annuaire-lrgrj   IPv4          8080    10.244.163.12,10.244.38.91   19s
```

Le Service choisit **tous** les Pods du namespace qui portent `app=annuaire`,
même ceux qui ne font pas partie de l'application. Donnez ce label à la
sonde :

```bash
kubectl label pod sonde app=annuaire -n essai-expose
sleep 3; kubectl get endpointslices -n essai-expose -l kubernetes.io/service-name=annuaire
```

```text
pod/sonde labeled
NAME             ADDRESSTYPE   PORTS   ENDPOINTS                                 AGE
annuaire-lrgrj   IPv4          8080    10.244.163.12,10.244.38.91,10.244.38.74   22s
```

La sonde est devenue un troisième endpoint. Or elle ne sert rien sur le
port 8080. Envoyez six requêtes (`|| echo ECHEC` signale chaque requête
ratée) :

```bash
for i in 1 2 3 4 5 6; do kubectl exec sonde -n essai-expose -- wget -qO- -T 2 "http://annuaire" || echo ECHEC; done
```

```text
wget: can't connect to remote host (10.110.40.62): Connection refused
command terminated with exit code 1
ECHEC
wget: can't connect to remote host (10.110.40.62): Connection refused
command terminated with exit code 1
ECHEC
annuaire
annuaire
annuaire
wget: can't connect to remote host (10.110.40.62): Connection refused
command terminated with exit code 1
ECHEC
```

Trois requêtes ont échoué : celles que le Service a envoyées à la sonde. Le
partage se fait au hasard, donc vous pouvez en voir plus ou moins. Retirez le
label (le tiret après la clé l'efface), puis recommencez :

```bash
kubectl label pod sonde app- -n essai-expose
sleep 3; for i in 1 2 3 4 5 6; do kubectl exec sonde -n essai-expose -- wget -qO- -T 2 "http://annuaire" || echo ECHEC; done
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

Supprimez d'abord ce que vous avez créé pendant les exercices : les deux
namespaces d'essai et le fichier du Service.

```bash
kubectl delete namespace essai-expose essai-voisin
rm ~/essai-annuaire-svc.yaml
```

```text
namespace "essai-expose" deleted
namespace "essai-voisin" deleted
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

À vous, seul cette fois : un service en quatre exemplaires, chacun répondant
son propre nom, joignable par les autres applications sous un nom et un port
stables.

```bash
dsoxlab run ckad-expose-service
dsoxlab challenge ckad-expose-service
```
