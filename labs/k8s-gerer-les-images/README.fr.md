# Figer une image par digest et tirer d'un registre privé

Une image se désigne par un **tag** (`nginx:1.30`) ou par un **digest**
(`nginx@sha256:…`). Un tag peut changer de contenu d'un jour à l'autre, un
digest désigne toujours exactement la même image. Dans ce cours, vous lisez
l'image qu'un Pod fait vraiment tourner, vous la figez par son digest, vous
lisez pourquoi une image ne se tire pas, puis vous donnez à un ServiceAccount
les identifiants d'un registre privé.

Vous travaillez dans un namespace d'essai, `essai-images`, avec les
Deployments `banniere`, `faute` et `miniatures`. Le registre privé
`localhost:30500` est celui que le lab a installé. Le challenge porte sur
d'autres Deployments, dans un autre namespace : vous le ferez seul, à la fin.

Page associée : [Les images dans Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/images-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-gerer-les-images
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`lab` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026, avec Kubernetes 1.37.

## 📚 Exercice 1 : un tag, et ce qu'il désigne aujourd'hui

Créez le namespace d'essai et un Deployment `banniere` sur le tag `nginx:1.30` :

```bash
kubectl create namespace essai-images
kubectl create deployment banniere --image=nginx:1.30 -n essai-images && kubectl rollout status deployment/banniere -n essai-images --timeout=180s | tail -1
```

```text
namespace/essai-images created
deployment.apps/banniere created
deployment "banniere" successfully rolled out
```

Comparez trois champs du Pod : l'image **demandée** (dans `spec`), l'image
**lancée** et son **digest** (dans `status`) :

```bash
kubectl get pods -n essai-images -l app=banniere -o jsonpath='{range .items[*]}{.spec.containers[0].image}{"\n"}{.status.containerStatuses[0].image}{"\n"}{.status.containerStatuses[0].imageID}{"\n"}{end}'
```

```text
nginx:1.30
docker.io/library/nginx:1.30
docker.io/library/nginx@sha256:7fad6c0dff97965adbddf28027d934b111fc0221a554315dc274712f3fba24d3
```

La spec ne dit que `nginx:1.30`. Le statut dit ce que ce tag désignait **au
moment du lancement** : le digest `sha256:7fad…`. Si l'éditeur publie demain
une nouvelle image sous le même tag, les prochains Pods ne tourneront plus sur
la même chose.

## 📚 Exercice 2 : figer l'image par son digest

Récupérez le digest dans le statut (`sed` garde ce qui suit le `@`), puis
mettez-le dans l'image du Deployment :

```bash
D=$(kubectl get pods -n essai-images -l app=banniere -o jsonpath='{.items[0].status.containerStatuses[0].imageID}' | sed 's/.*@//'); echo "$D"; kubectl set image deployment/banniere nginx=nginx@$D -n essai-images && kubectl rollout status deployment/banniere -n essai-images --timeout=180s | tail -1
```

```text
sha256:7fad6c0dff97965adbddf28027d934b111fc0221a554315dc274712f3fba24d3
deployment.apps/banniere image updated
deployment "banniere" successfully rolled out
```

Relisez l'image du Deployment, puis le digest de ses Pods :

```bash
kubectl get deployment banniere -n essai-images -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'; kubectl get pods -n essai-images -l app=banniere -o jsonpath='{range .items[*]}{.status.containerStatuses[0].imageID}{"\n"}{end}'
```

```text
nginx@sha256:7fad6c0dff97965adbddf28027d934b111fc0221a554315dc274712f3fba24d3
docker.io/library/nginx@sha256:7fad6c0dff97965adbddf28027d934b111fc0221a554315dc274712f3fba24d3
docker.io/library/nginx@sha256:7fad6c0dff97965adbddf28027d934b111fc0221a554315dc274712f3fba24d3
```

Le Deployment est figé sur le digest que ses Pods faisaient tourner. Les deux
lignes de Pods sont le nouveau Pod et l'ancien, encore en train de s'arrêter :
même digest, donc exactement la même image.

## 📚 Exercice 3 : une image qui n'existe pas

Créez un Deployment `faute` sur un tag qui n'existe pas :

```bash
kubectl create deployment faute --image=nginx:1.30-introuvable -n essai-images; sleep 20; kubectl get pods -n essai-images -l app=faute
```

```text
deployment.apps/faute created
NAME                    READY   STATUS             RESTARTS   AGE
faute-b7c5d55d5-fzckt   0/1     ImagePullBackOff   0          20s
```

`ImagePullBackOff` dit seulement que l'image ne se tire pas, et que Kubernetes
attend avant de réessayer. Le **pourquoi** est dans les événements du Pod.
`kubectl describe` les affiche à la fin de sa sortie. `sed` garde la section
`Events`, `grep` la ligne d'échec, et `fold` la coupe en lignes de 100
caractères :

```bash
P=$(kubectl get pods -n essai-images -l app=faute -o name | head -1); kubectl describe $P -n essai-images | sed -n '/^Events:/,$p' | grep -E 'Failed to pull' | head -1 | fold -w 100
```

```text
  Warning  Failed     4s (x2 over 19s)  kubelet            spec.containers{nginx}: Failed to pull im
age "nginx:1.30-introuvable": rpc error: code = NotFound desc = failed to pull and unpack image "doc
ker.io/library/nginx:1.30-introuvable": failed to resolve reference "docker.io/library/nginx:1.30-in
trouvable": docker.io/library/nginx:1.30-introuvable: not found
```

Le registre répond `NotFound` puis `not found` : ce tag n'existe pas. Une autre
cause donnerait un autre message. Lisez toujours ce message avant de corriger
quoi que ce soit.

## 📚 Exercice 4 : un registre privé, sans identifiants

Créez un ServiceAccount `miniatures`, puis un Deployment `miniatures` qui
l'utilise et tire une image du registre privé du lab. `sed` ajoute la ligne
`serviceAccountName` au modèle de Pod généré :

```bash
kubectl create serviceaccount miniatures -n essai-images
kubectl create deployment miniatures --image=localhost:30500/galerie/vignettes:1.0 -n essai-images --dry-run=client -o yaml | sed 's/^    spec:/    spec:\n      serviceAccountName: miniatures/' | kubectl apply -f -
sleep 20; kubectl get pods -n essai-images -l app=miniatures
```

```text
serviceaccount/miniatures created
deployment.apps/miniatures created
NAME                          READY   STATUS             RESTARTS   AGE
miniatures-6846cd68cb-b8452   0/1     ImagePullBackOff   0          20s
```

L'image ne se tire pas. Le message exact est dans les événements du Pod, comme
à l'exercice 3 : le challenge vous demandera de le lire vous-même.

## 📚 Exercice 5 : donner les identifiants au ServiceAccount

Les identifiants d'un registre se rangent dans un Secret de type
`docker-registry`. Créez-le avec l'adresse du registre et ses identifiants :

```bash
kubectl create secret docker-registry registre-essai --docker-server=localhost:30500 --docker-username=galerie --docker-password=Vignettes-2026 -n essai-images
```

```text
secret/registre-essai created
```

Plutôt que d'écrire ce Secret dans chaque Pod, rattachez-le au ServiceAccount
par son champ `imagePullSecrets` :

```bash
kubectl patch serviceaccount miniatures -n essai-images -p '{"imagePullSecrets":[{"name":"registre-essai"}]}'; kubectl get serviceaccount miniatures -n essai-images -o jsonpath='{.imagePullSecrets}{"\n"}'
```

```text
serviceaccount/miniatures patched
[{"name":"registre-essai"}]
```

Attendez un peu, puis regardez le Pod existant : son état, et les Secrets
qu'il porte :

```bash
sleep 15; kubectl get pods -n essai-images -l app=miniatures -o custom-columns='POD:.metadata.name,ETAT:.status.containerStatuses[0].state.waiting.reason,SECRETS:.spec.imagePullSecrets'
```

```text
POD                           ETAT           SECRETS
miniatures-6846cd68cb-b8452   ErrImagePull   <none>
```

Toujours en échec, et sans Secret (`<none>`). Le ServiceAccount donne ses
`imagePullSecrets` à un Pod **au moment où le Pod est créé**. Ce Pod existait
avant : il ne les recevra jamais.

## 📚 Exercice 6 : seuls les nouveaux Pods reçoivent le Secret

`kubectl rollout restart` remplace les Pods du Deployment par des Pods neufs :

```bash
kubectl rollout restart deployment/miniatures -n essai-images && kubectl rollout status deployment/miniatures -n essai-images --timeout=180s | tail -1; sleep 5
kubectl get pods -n essai-images -l app=miniatures -o custom-columns='POD:.metadata.name,PRET:.status.containerStatuses[0].ready,SECRETS:.spec.imagePullSecrets'
```

```text
deployment.apps/miniatures restarted
deployment "miniatures" successfully rolled out
POD                           PRET   SECRETS
miniatures-646b467959-bq76n   true   [map[name:registre-essai]]
```

Le nouveau Pod porte le Secret, a tiré son image et tourne. Pourtant, le
Deployment lui-même ne cite aucun Secret (`echo '(fin)'` marque la fin de la
sortie) :

```bash
kubectl get deployment miniatures -n essai-images -o jsonpath='{.spec.template.spec.imagePullSecrets}'; echo '(fin)'
```

```text
(fin)
```

Rien avant `(fin)` : c'est le ServiceAccount qui a ajouté le Secret au Pod.
Les identifiants restent ainsi à un seul endroit, et aucun manifeste de Pod ne
les cite.

## 🧹 Nettoyage

Supprimez le namespace d'essai, avec ses Deployments, son ServiceAccount et
son Secret :

```bash
kubectl delete namespace essai-images
```

```text
namespace "essai-images" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-gerer-les-images
dsoxlab check k8s-gerer-les-images
```

```text
╭─ Résultat : k8s-gerer-les-images ─╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests  │
╰───────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : figer une autre application par digest, relever
pourquoi une seconde ne tire pas son image, puis la réparer par son
ServiceAccount.

```bash
dsoxlab run k8s-gerer-les-images
dsoxlab challenge k8s-gerer-les-images
```
