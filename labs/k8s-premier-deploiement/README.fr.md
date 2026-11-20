# Déployer, exposer et mettre à l'échelle une première application

La leçon déploie une application, l'expose par un Service et la met à
l'échelle. Ce cours vous fait diagnostiquer ce qui se passe quand l'un de ces
gestes est mal fait, puis passer à un fichier que `kubectl diff` relit avant
chaque `kubectl apply`.

Quelques mots reviennent tout le long :

- un **Pod** est la plus petite unité que Kubernetes fait tourner : un ou
  plusieurs conteneurs ;
- un **Deployment** dit « je veux N Pods de cette image », et Kubernetes les
  crée et les remplace s'ils tombent ;
- un **Service** donne une adresse stable pour joindre ces Pods, même quand
  ils changent ;
- un **namespace** est un espace de rangement à l'intérieur du cluster.

Vous travaillez dans un namespace d'essai, `essai-web`, avec une application
nommée `accueil`. Le challenge vous demandera une autre application, dans un
autre namespace : vous la déploierez seul, à la fin.

Page associée : [Déployer votre première application](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/fondamentaux/premier-deploiement/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-premier-deploiement
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`boutique` y tourne, en Kubernetes `v1.37.0`, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026.

## 📚 Exercice 1 : créer dans un namespace qui n'existe pas

Lancez l'application `accueil` dans le namespace `essai-web`, sans l'avoir
créé :

```bash
kubectl create deployment accueil \
  --image=nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-web
```

```text
error: failed to create deployment: namespaces "essai-web" not found
```

Kubernetes ne crée pas le namespace à votre place. Créez-le, puis relancez la
même commande et attendez que l'application soit disponible :

```bash
kubectl create namespace essai-web
kubectl create deployment accueil \
  --image=nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-web
kubectl wait --for=condition=Available deployment/accueil -n essai-web --timeout=120s
```

```text
namespace/essai-web created
deployment.apps/accueil created
deployment.apps/accueil condition met
```

Pour interroger l'application de l'intérieur du cluster, lancez un Pod
`outil` qui reste allumé une heure. L'image busybox contient la commande
`wget` :

```bash
kubectl run outil \
  --image=busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e \
  -n essai-web -- sleep 3600
kubectl wait --for=condition=Ready pod/outil -n essai-web --timeout=120s
```

```text
pod/outil created
pod/outil condition met
```

`kubectl exec outil -- <commande>` lance une commande dans ce Pod. Vous vous en
servez dans les exercices suivants.

## 📚 Exercice 2 : un Service qui trouve le Pod mais vise le mauvais port

Exposez `accueil` sur le port `8080`, sans préciser `--target-port` :

```bash
kubectl expose deployment accueil --port=8080 -n essai-web
kubectl get endpointslice -n essai-web -l kubernetes.io/service-name=accueil
```

```text
service/accueil exposed
NAME            ADDRESSTYPE   PORTS   ENDPOINTS    AGE
accueil-zbtbn   IPv4          8080    10.244.0.5   0s
```

Le Service a trouvé le Pod : son adresse figure dans `ENDPOINTS`. La panne
« sélecteur qui ne trouve rien » de la leçon n'est donc pas en cause.
Interrogez pourtant l'application :

```bash
kubectl exec outil -n essai-web -- wget -qO- -T 3 http://accueil:8080
```

```text
wget: can't connect to remote host (10.96.187.78): Connection refused
command terminated with exit code 1
```

`Connection refused` : la demande arrive bien au Pod, mais rien n'y écoute sur
le port visé. Lisez les deux ports du Service :

```bash
kubectl describe service accueil -n essai-web | grep -E "^(Port|TargetPort|Endpoints)"
```

```text
Port:                     <unset>  8080/TCP
TargetPort:               8080/TCP
Endpoints:                10.244.0.5:8080
```

Sans `--target-port`, kubectl reprend la valeur de `--port`. Le Service envoie
donc vers le port `8080` du Pod, alors que nginx écoute sur le `80`.
Recréez-le avec le bon port, puis enregistrez la page dans un fichier, sur la
machine du lab :

```bash
kubectl delete service accueil -n essai-web
kubectl expose deployment accueil --port=8080 --target-port=80 -n essai-web
kubectl exec outil -n essai-web -- wget -qO- -T 3 http://accueil:8080 > ~/essai-reponse.html
head -4 ~/essai-reponse.html
```

```text title="Extrait de la sortie"
service/accueil exposed
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
```

La redirection `>` est lue par votre shell, pas par le Pod : le fichier
`~/essai-reponse.html` est écrit sur la machine où vous tapez la commande.

## 📚 Exercice 3 : un Service sans aucun Pod derrière

Passez le Deployment à zéro Pod, attendez que le Pod soit supprimé, puis
regardez le Service :

```bash
kubectl scale deployment accueil --replicas=0 -n essai-web
kubectl wait --for=delete pod -l app=accueil -n essai-web --timeout=60s
kubectl get endpointslice -n essai-web -l kubernetes.io/service-name=accueil
kubectl exec outil -n essai-web -- wget -qO- -T 3 http://accueil:8080
```

```text
deployment.apps/accueil scaled
pod/accueil-654cbccb8f-w726j condition met
NAME            ADDRESSTYPE   PORTS     ENDPOINTS   AGE
accueil-8657t   IPv4          <unset>   <unset>     4s
wget: download timed out
command terminated with exit code 1
```

Le Service existe toujours, avec son adresse, mais il n'a plus aucun endpoint.
Comparez avec l'exercice 2 : un port faux donne `Connection refused`, aucun
Pod donne `download timed out`, au bout des 3 secondes fixées par `-T 3`. Le
message de `wget` vous dit donc où chercher.

## 📚 Exercice 4 : voir à quel Pod va chaque requête

Repassez à deux Pods, puis envoyez six requêtes au Service :

```bash
kubectl scale deployment accueil --replicas=2 -n essai-web
kubectl wait --for=condition=Available deployment/accueil -n essai-web --timeout=120s
for i in 1 2 3 4 5 6; do kubectl exec outil -n essai-web -- wget -qO /dev/null "http://accueil:8080"; done
```

```text
deployment.apps/accueil scaled
deployment.apps/accueil condition met
```

`kubectl logs deployment/accueil` ne lit le journal que d'un seul Pod. Avec
`-l app=accueil`, kubectl lit tous les Pods qui portent cette étiquette, et
`--prefix` écrit devant chaque ligne le Pod d'où elle vient :

```bash
kubectl logs -l app=accueil -n essai-web --prefix | grep GET
```

```text
[pod/accueil-654cbccb8f-sdswl/nginx] 10.244.0.6 - - [20/Nov/2026:07:07:41 +0000] "GET / HTTP/1.1" 200 896 "-" "Wget" "-"
[pod/accueil-654cbccb8f-sdswl/nginx] 10.244.0.6 - - [20/Nov/2026:07:07:42 +0000] "GET / HTTP/1.1" 200 896 "-" "Wget" "-"
[pod/accueil-654cbccb8f-sdswl/nginx] 10.244.0.6 - - [20/Nov/2026:07:07:42 +0000] "GET / HTTP/1.1" 200 896 "-" "Wget" "-"
[pod/accueil-654cbccb8f-vvhdx/nginx] 10.244.0.6 - - [20/Nov/2026:07:07:41 +0000] "GET / HTTP/1.1" 200 896 "-" "Wget" "-"
[pod/accueil-654cbccb8f-vvhdx/nginx] 10.244.0.6 - - [20/Nov/2026:07:07:42 +0000] "GET / HTTP/1.1" 200 896 "-" "Wget" "-"
[pod/accueil-654cbccb8f-vvhdx/nginx] 10.244.0.6 - - [20/Nov/2026:07:07:42 +0000] "GET / HTTP/1.1" 200 896 "-" "Wget" "-"
```

Ici, trois requêtes par Pod. Le Service choisit un Pod au hasard pour chaque
connexion : chez vous, la répartition peut être de quatre et deux. Toutes les
requêtes viennent de `10.244.0.6`, l'adresse du Pod `outil`. Ce sont
seulement les requêtes de cet exercice : les Pods ont été recréés à
l'exercice 3, avec un journal vide.

## 📚 Exercice 5 : passer à un fichier, et lire avant d'appliquer

Jusqu'ici, vous avez donné vos ordres un par un. Le challenge du module vous
demandera de corriger un Deployment dans son fichier, puis de l'appliquer avec
`kubectl apply -f`. Faites écrire un fichier par kubectl : `--dry-run=client`
prépare l'objet sans l'envoyer au cluster, et `-o yaml` l'affiche.

```bash
kubectl create deployment accueil \
  --image=nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-web --dry-run=client -o yaml > ~/essai-accueil.yaml
grep -E "replicas|image:" ~/essai-accueil.yaml
```

```text
  replicas: 1
      - image: nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

Avant d'appliquer un fichier, demandez ce qu'il changerait. `kubectl diff`
compare le fichier à l'objet du cluster, sans rien modifier :

```bash
kubectl diff -f ~/essai-accueil.yaml
echo "code de kubectl diff : $?"
```

```text title="Extrait de la sortie"
-  replicas: 2
+  replicas: 1
code de kubectl diff : 1
```

Les lignes `-` montrent le cluster, les lignes `+` ce que deviendrait l'objet.
Le fichier généré porte `replicas: 1`, la valeur par défaut. L'appliquer
supprimerait donc un de vos deux Pods. Le code de sortie `1` signale une
différence. Corrigez le fichier pour trois Pods, relisez la différence, puis
appliquez :

```bash
sed -i "s/replicas: 1/replicas: 3/" ~/essai-accueil.yaml
kubectl diff -f ~/essai-accueil.yaml
kubectl apply -f ~/essai-accueil.yaml
```

```text title="Extrait de la sortie"
-  replicas: 2
+  replicas: 3
Warning: resource deployments/accueil is missing the kubectl.kubernetes.io/last-applied-configuration annotation which is required by kubectl apply. kubectl apply should only be used on resources created declaratively by either kubectl create --save-config or kubectl apply. The missing annotation will be patched automatically.
deployment.apps/accueil configured
```

`configured` : l'objet existait, et `apply` l'a modifié. L'avertissement est
normal la première fois, comme l'explique la leçon : l'objet a été créé par
`kubectl create`, et `apply` lui ajoute l'annotation où il garde la dernière
configuration appliquée. Relancez `kubectl diff` :

```bash
kubectl diff -f ~/essai-accueil.yaml
echo "code de kubectl diff : $?"
kubectl get deployment accueil -n essai-web
```

```text
code de kubectl diff : 0
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
accueil   2/3     3            2           25s
```

Plus aucune différence, et le code de sortie vaut `0` : le cluster correspond
au fichier. `READY 2/3` : le troisième Pod démarre, il sera prêt quelques
secondes plus tard.

## 🧹 Nettoyage

Supprimez ce que vous avez créé pendant les exercices : le namespace d'essai
et les deux fichiers. Tout ce que contient le namespace disparaît avec lui :
le Deployment, ses Pods, le Pod `outil` et le Service.

```bash
kubectl delete namespace essai-web
rm ~/essai-reponse.html ~/essai-accueil.yaml
```

```text
namespace "essai-web" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-premier-deploiement
dsoxlab check k8s-premier-deploiement
```

```text
╭─ Résultat : k8s-premier-deploiement ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests     │
╰──────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : déployer, exposer et mettre à l'échelle
l'application du challenge, puis garder sa réponse dans un fichier.

```bash
dsoxlab run k8s-premier-deploiement
dsoxlab challenge k8s-premier-deploiement
```
