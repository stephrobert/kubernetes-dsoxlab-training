# Créer ou appliquer : apply, server-side apply et prune

`kubectl create` crée un objet, une fois. `kubectl apply` amène un objet à
l'état décrit dans un fichier, autant de fois qu'on le rejoue. Dans ce cours,
vous comparez les deux, vous appliquez un dossier entier, vous voyez le piège
d'un champ retiré du fichier, vous découvrez qui « possède » chaque champ d'un
objet, vous reprenez un champ avec le server-side apply, puis vous supprimez
ce qui n'est plus dans le dossier.

Vous travaillez dans un namespace d'essai, `essai-apply`, avec une application
`colis` et un Deployment `etiquettes`. Le challenge vous demandera la même
chose sur d'autres objets : vous le ferez seul, à la fin.

Page associée : [kubectl create et apply](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-create-apply/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-creer-ou-appliquer
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`lab` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026, avec Kubernetes 1.37.

Préparez le namespace d'essai et un dossier `appli` avec deux fichiers : le
Deployment `colis` à la racine, et sa ConfigMap dans un sous-dossier `extra`.
Les deux objets portent le label `app: colis` :

```bash
kubectl create namespace essai-apply; mkdir -p ~/essai-apply/appli/extra
cat > ~/essai-apply/appli/colis.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: colis
  namespace: essai-apply
  labels:
    app: colis
spec:
  replicas: 2
  selector:
    matchLabels:
      app: colis
  template:
    metadata:
      labels:
        app: colis
    spec:
      containers:
        - name: colis
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
YAML
cat > ~/essai-apply/appli/extra/colis-config.yaml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: colis-config
  namespace: essai-apply
  labels:
    app: colis
data:
  POIDS_MAX: 30kg
YAML
find ~/essai-apply/appli -type f
```

```text
namespace/essai-apply created
/home/ansible/essai-apply/appli/colis.yaml
/home/ansible/essai-apply/appli/extra/colis-config.yaml
```

## 📚 Exercice 1 : create, puis apply

Créez le Deployment avec `create`, deux fois de suite :

```bash
kubectl create -f ~/essai-apply/appli/colis.yaml
kubectl create -f ~/essai-apply/appli/colis.yaml
```

```text
deployment.apps/colis created
Error from server (AlreadyExists): error when creating "/home/ansible/essai-apply/appli/colis.yaml": deployments.apps "colis" already exists
```

`create` refuse un objet qui existe déjà. Faites maintenant la même chose avec
`apply` :

```bash
kubectl apply -f ~/essai-apply/appli/colis.yaml
kubectl apply -f ~/essai-apply/appli/colis.yaml
```

```text
Warning: resource deployments/colis is missing the kubectl.kubernetes.io/last-applied-configuration annotation which is required by kubectl apply. kubectl apply should only be used on resources created declaratively by either kubectl create --save-config or kubectl apply. The missing annotation will be patched automatically.
deployment.apps/colis configured
deployment.apps/colis unchanged
```

Le premier `apply` prévient : l'objet a été créé par `create`, il lui manque
l'annotation `last-applied-configuration`, et `apply` l'ajoute. Le second
`apply` ne change rien (`unchanged`) : on peut le rejouer sans risque.

Cette annotation garde une copie du fichier appliqué la dernière fois. En voici
le début :

```bash
kubectl get deployment colis -n essai-apply -o jsonpath='{.metadata.annotations.kubectl\.kubernetes\.io/last-applied-configuration}' | cut -c1-90
```

```text
{"apiVersion":"apps/v1","kind":"Deployment","metadata":{"annotations":{},"labels":{"app":"
```

## 📚 Exercice 2 : un dossier et ses sous-dossiers

`apply -f` accepte un dossier. Appliquez `appli` :

```bash
kubectl apply -f ~/essai-apply/appli/
```

```text
deployment.apps/colis unchanged
```

Seul `colis.yaml` a été lu : la ConfigMap du sous-dossier `extra` est ignorée.
`-R` (récursif) descend dans les sous-dossiers :

```bash
kubectl apply -f ~/essai-apply/appli/ -R
```

```text
deployment.apps/colis unchanged
configmap/colis-config created
```

## 📚 Exercice 3 : retirer un champ du fichier

Imaginez qu'un autoscaler décide désormais du nombre de Pods. Il passe `colis`
à 5 réplicas (ici, vous le faites à sa place avec `kubectl scale`) :

```bash
kubectl scale deployment colis --replicas=5 -n essai-apply; kubectl rollout status deployment/colis -n essai-apply --timeout=180s | tail -1
```

```text
deployment.apps/colis scaled
deployment "colis" successfully rolled out
```

Le fichier ne doit donc plus fixer `replicas`. Retirez la ligne :

```bash
sed -i '/^  replicas:/d' ~/essai-apply/appli/colis.yaml; grep -c replicas ~/essai-apply/appli/colis.yaml
```

```text
0
```

Avant de réappliquer, demandez au serveur ce que donnerait `apply`, sans rien
changer (`--dry-run=server`), en n'affichant que le nombre de réplicas :

```bash
kubectl apply -f ~/essai-apply/appli/colis.yaml --dry-run=server -o jsonpath='{.spec.replicas}{"\n"}'
```

```text
1
```

1, et non 5. `apply` compare le fichier à l'annotation `last-applied`.
L'annotation contient encore `replicas: 2`, le fichier ne l'a plus : pour
`apply`, c'est un champ à **retirer**. Sans valeur, un Deployment revient à 1
réplica. L'autoscaler perdrait son travail.

`kubectl apply set-last-applied` met l'annotation à jour d'après le fichier,
sans toucher au reste de l'objet. Faites-le, puis refaites la simulation :

```bash
kubectl apply set-last-applied -f ~/essai-apply/appli/colis.yaml
kubectl apply -f ~/essai-apply/appli/colis.yaml --dry-run=server -o jsonpath='{.spec.replicas}{"\n"}'
```

```text
deployment.apps/colis configured
5
```

L'annotation ne parle plus de `replicas`, donc `apply` n'y touche plus.
Appliquez pour de bon :

```bash
kubectl apply -f ~/essai-apply/appli/colis.yaml; kubectl get deployment colis -n essai-apply
```

```text
deployment.apps/colis configured
NAME    READY   UP-TO-DATE   AVAILABLE   AGE
colis   5/5     5            5           2s
```

## 📚 Exercice 4 : qui possède quoi

Kubernetes note, pour chaque champ d'un objet, quel outil l'a écrit : c'est le
**gestionnaire de champs** (field manager). Créez un Deployment `etiquettes`
avec `create` :

```bash
kubectl create deployment etiquettes --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-apply; kubectl rollout status deployment/etiquettes -n essai-apply --timeout=180s | tail -1
```

```text
deployment.apps/etiquettes created
deployment "etiquettes" successfully rolled out
```

La liste des gestionnaires se trouve dans `metadata.managedFields` :

```bash
kubectl get deployment etiquettes -n essai-apply -o jsonpath='{range .metadata.managedFields[*]}{.manager}{"\t"}{.operation}{"\n"}{end}'
```

```text
kube-controller-manager	Update
kubectl-create	Update
```

`kubectl-create` a écrit l'objet. `kube-controller-manager` met à jour son
état. Qui possède le champ `image` ? Le filtre JSONPath ne garde que les champs
de `kubectl-create`, et `grep` y cherche `f:image` :

```bash
kubectl get deployment etiquettes -n essai-apply -o jsonpath='{.metadata.managedFields[?(@.manager=="kubectl-create")].fieldsV1}' | grep -o -w 'f:image' || echo '(aucun)'
```

```text
f:image
```

L'image appartient à `kubectl-create`.

## 📚 Exercice 5 : server-side apply et conflit

Une équipe veut désormais piloter l'image de `etiquettes`. Elle écrit un
fichier qui ne décrit que ce qu'elle possède (le sélecteur, le modèle de Pod,
l'image en version 1.30.6), et l'applique avec le **server-side apply** sous
son propre nom de gestionnaire, `equipe-etiquettes` :

```bash
cat > ~/essai-apply/etiquettes.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: etiquettes
  namespace: essai-apply
spec:
  selector:
    matchLabels:
      app: etiquettes
  template:
    metadata:
      labels:
        app: etiquettes
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
YAML
kubectl apply --server-side --field-manager=equipe-etiquettes -f ~/essai-apply/etiquettes.yaml
```

```text
error: Apply failed with 1 conflict: conflict with "kubectl-create" using apps/v1: .spec.template.spec.containers[name="nginx"].image
Please review the fields above--they currently have other managers. Here
are the ways you can resolve this warning:
* If you intend to manage all of these fields, please re-run the apply
  command with the `--force-conflicts` flag.
* If you do not intend to manage all of the fields, please edit your
  manifest to remove references to the fields that should keep their
  current managers.
* You may co-own fields by updating your manifest to match the existing
  value; in this case, you'll become the manager if the other manager(s)
  stop managing the field (remove it from their configuration).
See https://kubernetes.io/docs/reference/using-api/server-side-apply/#conflicts
```

Le serveur refuse : l'image appartient à `kubectl-create`, et l'équipe veut lui
donner une autre valeur. C'est un **conflit**. Le message donne trois sorties.
Ici, l'équipe doit bien prendre la main sur l'image : `--force-conflicts` lui
transfère le champ :

```bash
kubectl apply --server-side --field-manager=equipe-etiquettes --force-conflicts -f ~/essai-apply/etiquettes.yaml
```

```text
deployment.apps/etiquettes serverside-applied
```

Relisez les gestionnaires, puis le propriétaire de `image` :

```bash
kubectl get deployment etiquettes -n essai-apply -o jsonpath='{range .metadata.managedFields[*]}{.manager}{"\t"}{.operation}{"\n"}{end}'
kubectl get deployment etiquettes -n essai-apply -o jsonpath='{.metadata.managedFields[?(@.manager=="kubectl-create")].fieldsV1}' | grep -o -w 'f:image' || echo '(aucun)'
kubectl get deployment etiquettes -n essai-apply -o jsonpath='{.metadata.managedFields[?(@.manager=="equipe-etiquettes")].fieldsV1}' | grep -o -w 'f:image' || echo '(aucun)'
```

```text
equipe-etiquettes	Apply
kubectl-create	Update
kube-controller-manager	Update
(aucun)
f:image
```

`equipe-etiquettes` apparaît, avec l'opération `Apply`. Le champ `image` a
quitté `kubectl-create` pour lui. `kubectl-create` reste dans la liste, pour
les champs qu'il possède encore. Le Deployment tourne bien en 1.30.6 :

```bash
kubectl rollout status deployment/etiquettes -n essai-apply --timeout=180s | tail -1; kubectl get deployment etiquettes -n essai-apply -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

```text
deployment "etiquettes" successfully rolled out
nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
```

## 📚 Exercice 6 : élaguer ce qui n'est plus dans le dossier

Créez deux ConfigMaps par `apply`, comme si elles venaient d'anciens fichiers :
`colis-vieux`, avec le label `app: colis`, dont le fichier a disparu du
dossier, et `autre`, avec le label `app: autre`, qui appartient à une autre
application. `kubectl label --local` ajoute le label au YAML sans rien envoyer
au cluster :

```bash
kubectl create configmap colis-vieux --from-literal=POIDS_MAX=20kg -n essai-apply --dry-run=client -o yaml | kubectl label --local -f - app=colis -o yaml | kubectl apply -f -
kubectl create configmap autre --from-literal=a=1 -n essai-apply --dry-run=client -o yaml | kubectl label --local -f - app=autre -o yaml | kubectl apply -f -
kubectl get configmap -n essai-apply -L app
```

```text
configmap/colis-vieux created
configmap/autre created
NAME               DATA   AGE   APP
autre              1      0s    autre
colis-config       1      3s    colis
colis-vieux        1      0s    colis
kube-root-ca.crt   1      3s    
```

`-L app` ajoute une colonne avec la valeur du label `app`. `--prune` supprime
les objets créés par `apply` qui ne sont plus dans les fichiers. Essayez-le
sans rien préciser, en simulation :

```bash
kubectl apply -f ~/essai-apply/appli -R --prune --dry-run=server
```

```text
error: all resources selected for prune without explicitly passing --all. To prune all resources, pass the --all flag. If you did not mean to prune all resources, specify a label selector
```

kubectl refuse : sans limite, il pourrait supprimer bien plus que prévu. Il
demande un sélecteur de labels, ou `--all`. Limitez l'élagage aux objets
`app=colis`, toujours en simulation :

```bash
kubectl apply -f ~/essai-apply/appli -R --prune -l app=colis --dry-run=server
```

```text
deployment.apps/colis unchanged (server dry run)
configmap/colis-config unchanged (server dry run)
W1119 19:24:06.068201   49079 prune.go:71] Deprecated: kubectl apply will no longer prune non-namespaced resources by default when used with the --namespace flag in a future release. To preserve the current behaviour, list the resources you want to target explicitly in the --prune-allowlist flag.
configmap/colis-vieux pruned (server dry run)
Warning: v1 Endpoints is deprecated in v1.33+; use discovery.k8s.io/v1 EndpointSlice
```

Seule `colis-vieux` partirait (`pruned`). `autre` n'est pas citée : son label
ne correspond pas. Les deux lignes `W1119` et `Warning` sont des avertissements
de kubectl sur des évolutions futures, sans effet ici. Lancez l'élagage pour de
bon, puis vérifiez :

```bash
kubectl apply -f ~/essai-apply/appli -R --prune -l app=colis
kubectl get configmap -n essai-apply -L app
```

```text
deployment.apps/colis unchanged
configmap/colis-config unchanged
W1119 19:24:07.616119   49090 prune.go:71] Deprecated: kubectl apply will no longer prune non-namespaced resources by default when used with the --namespace flag in a future release. To preserve the current behaviour, list the resources you want to target explicitly in the --prune-allowlist flag.
configmap/colis-vieux pruned
Warning: v1 Endpoints is deprecated in v1.33+; use discovery.k8s.io/v1 EndpointSlice
NAME               DATA   AGE   APP
autre              1      4s    autre
colis-config       1      7s    colis
kube-root-ca.crt   1      7s    
```

`colis-vieux` a disparu, `autre` est intacte.

## 🧹 Nettoyage

Supprimez le namespace d'essai et le dossier de travail :

```bash
kubectl delete namespace essai-apply; rm -rf ~/essai-apply
```

```text
namespace "essai-apply" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-creer-ou-appliquer
dsoxlab check k8s-creer-ou-appliquer
```

```text
╭─ Résultat : k8s-creer-ou-appliquer ─╮
│  0 / 100 pts                        │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests    │
╰─────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : appliquer tout un dossier, laisser un autoscaler
décider des réplicas, confier une image à une équipe par server-side apply, et
élaguer sans rien casser.

```bash
dsoxlab run k8s-creer-ou-appliquer
dsoxlab challenge k8s-creer-ou-appliquer
```
