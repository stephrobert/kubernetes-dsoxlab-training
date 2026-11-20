# Figer une image par digest et tirer d'un registre privé

Une image se désigne par un **tag** (`nginx:1.29`) ou par un **digest**
(`nginx@sha256:…`). Un tag peut changer de contenu d'un jour à l'autre, un
digest désigne toujours exactement la même image. La leçon montre comment
figer une image et comment donner des identifiants à un ServiceAccount. Ce
cours part de ce qui rate : un digest mal recopié, un registre qui refuse un
client sans identifiants, et un Secret qui vise le mauvais serveur, sans que
le message change.

Vous travaillez dans un namespace d'essai, `essai-images`, avec les
Deployments `banniere` et `miniatures`. Le registre privé `localhost:30500`
est celui que le lab a installé. Le challenge porte sur d'autres Deployments,
dans un autre namespace : vous le ferez seul, à la fin.

Page associée : [Les images dans Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/images-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-gerer-les-images
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`lab` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026, avec Kubernetes v1.37.0.

## 📚 Exercice 1 : un tag, et ce qu'il désigne aujourd'hui

Créez le namespace d'essai et un Deployment `banniere` sur le tag `nginx:1.29` :

```bash
kubectl create namespace essai-images
kubectl create deployment banniere --image=nginx:1.29 -n essai-images && kubectl rollout status deployment/banniere -n essai-images --timeout=180s | tail -1
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
nginx:1.29
docker.io/library/nginx:1.29
docker.io/library/nginx@sha256:1881968aff6f7cdcc4b888c00a11f4ce241ad7ec957e0cb4a9e19e93a3ff87ea
```

La spec ne dit que `nginx:1.29`. Le statut dit ce que ce tag désignait **au
moment du lancement** : le digest `sha256:1881…`. Votre digest peut être
différent : le tag `nginx:1.29` suit les correctifs de la version 1.29.

## 📚 Exercice 2 : un digest mal recopié

Un digest se recopie mal facilement : 64 caractères, sans erreur visible à
l'œil. Simulez la faute. La commande lit le digest du Pod, en change le
dernier caractère, puis passe le Deployment sur ce faux digest :

```bash
D=$(kubectl get pods -n essai-images -l app=banniere -o jsonpath='{.items[0].status.containerStatuses[0].imageID}' | sed 's/.*@//'); echo "$D"; FAUX=$(echo "$D" | sed 's/.$/0/'); [ "$FAUX" = "$D" ] && FAUX=$(echo "$D" | sed 's/.$/1/'); echo "$FAUX"; kubectl set image deployment/banniere nginx=nginx@$FAUX -n essai-images
sleep 20; kubectl get pods -n essai-images -l app=banniere
```

```text
sha256:1881968aff6f7cdcc4b888c00a11f4ce241ad7ec957e0cb4a9e19e93a3ff87ea
sha256:1881968aff6f7cdcc4b888c00a11f4ce241ad7ec957e0cb4a9e19e93a3ff87e0
deployment.apps/banniere image updated
NAME                        READY   STATUS             RESTARTS   AGE
banniere-57dbb788b5-mlhvr   0/1     ImagePullBackOff   0          20s
banniere-7f66886dd-wsnxw    1/1     Running            0          20s
```

Le nouveau Pod ne tire pas son image, l'ancien sert toujours. Le pourquoi est
dans les événements du Pod en attente. `sed` garde la section `Events`, `grep`
la ligne d'échec, et `fold` la coupe en lignes de 100 caractères :

```bash
P=$(kubectl get pods -n essai-images -l app=banniere --field-selector=status.phase=Pending -o name | head -1); kubectl describe $P -n essai-images | sed -n '/^Events:/,$p' | grep -E 'Failed to pull' | head -1 | fold -w 100
```

```text
  Warning  Failed     5s (x2 over 19s)  kubelet            spec.containers{nginx}: Failed to pull im
age "nginx@sha256:1881968aff6f7cdcc4b888c00a11f4ce241ad7ec957e0cb4a9e19e93a3ff87e0": rpc error: code
 = NotFound desc = failed to pull and unpack image "docker.io/library/nginx@sha256:1881968aff6f7cdcc
4b888c00a11f4ce241ad7ec957e0cb4a9e19e93a3ff87e0": failed to resolve reference "docker.io/library/ngi
nx@sha256:1881968aff6f7cdcc4b888c00a11f4ce241ad7ec957e0cb4a9e19e93a3ff87e0": docker.io/library/nginx
@sha256:1881968aff6f7cdcc4b888c00a11f4ce241ad7ec957e0cb4a9e19e93a3ff87e0: not found
```

`not found` : aucune image ne porte ce digest. C'est le même message qu'un tag
qui n'existe pas. Revenez à la version précédente, puis figez cette fois le
bon digest, lu sur un Pod en marche (`status.phase=Running`) :

```bash
kubectl rollout undo deployment/banniere -n essai-images; kubectl rollout status deployment/banniere -n essai-images --timeout=120s | tail -1
D=$(kubectl get pods -n essai-images -l app=banniere --field-selector=status.phase=Running -o jsonpath='{.items[0].status.containerStatuses[0].imageID}' | sed 's/.*@//'); kubectl set image deployment/banniere nginx=nginx@$D -n essai-images && kubectl rollout status deployment/banniere -n essai-images --timeout=180s | tail -1; kubectl get deployment banniere -n essai-images -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

```text
deployment.apps/banniere rolled back
deployment "banniere" successfully rolled out
deployment.apps/banniere image updated
deployment "banniere" successfully rolled out
nginx@sha256:1881968aff6f7cdcc4b888c00a11f4ce241ad7ec957e0cb4a9e19e93a3ff87ea
```

Le Deployment est figé sur le digest que ses Pods faisaient tourner. Lisez
toujours ce digest sur un Pod `Running` : juste après un `undo`, un Pod qui
n'a pas encore démarré n'en a pas.

## 📚 Exercice 3 : un registre privé, sans identifiants

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
miniatures-6846cd68cb-krkc8   0/1     ImagePullBackOff   0          20s
```

Lisez le message d'échec dans les événements du namespace :

```bash
kubectl get events -n essai-images --field-selector reason=Failed -o custom-columns=MESSAGE:.message --no-headers | grep -m1 'localhost:30500' | fold -w 100
```

```text
Failed to pull image "localhost:30500/galerie/vignettes:1.0": failed to pull and unpack image "local
host:30500/galerie/vignettes:1.0": failed to resolve reference "localhost:30500/galerie/vignettes:1.
0": pull access denied, repository does not exist or may require authorization: authorization failed
: no basic auth credentials
```

`no basic auth credentials` : le client n'a envoyé aucun identifiant. Retenez
ce message : un registre qui reçoit un **mauvais** mot de passe répond
autrement.

## 📚 Exercice 4 : un Secret qui vise le mauvais serveur

Créez un Secret `docker-registry`, mais pour un autre serveur,
`localhost:5000`, une faute de copie courante. Rattachez-le au ServiceAccount,
puis remplacez les Pods :

```bash
kubectl create secret docker-registry registre-essai --docker-server=localhost:5000 --docker-username=galerie --docker-password=Vignettes-2026 -n essai-images
kubectl patch serviceaccount miniatures -n essai-images -p '{"imagePullSecrets":[{"name":"registre-essai"}]}'
kubectl rollout restart deployment/miniatures -n essai-images; sleep 25; kubectl get pods -n essai-images -l app=miniatures -o custom-columns='POD:.metadata.name,ETAT:.status.containerStatuses[0].state.waiting.reason,SECRETS:.spec.imagePullSecrets'
```

```text
secret/registre-essai created
serviceaccount/miniatures patched
deployment.apps/miniatures restarted
POD                           ETAT               SECRETS
miniatures-666c6d7978-4nj7t   ImagePullBackOff   [map[name:registre-essai]]
miniatures-6846cd68cb-krkc8   ImagePullBackOff   <none>
```

Le nouveau Pod porte bien le Secret, et pourtant il échoue. Son message, lu
sur ce seul Pod :

```bash
P=$(kubectl get pods -n essai-images -l app=miniatures -o jsonpath='{range .items[?(@.spec.imagePullSecrets)]}{.metadata.name}{end}'); kubectl get events -n essai-images --field-selector involvedObject.name=$P,reason=Failed -o custom-columns=MESSAGE:.message --no-headers | grep -m1 'localhost:30500' | fold -w 100
```

```text
Failed to pull image "localhost:30500/galerie/vignettes:1.0": failed to pull and unpack image "local
host:30500/galerie/vignettes:1.0": failed to resolve reference "localhost:30500/galerie/vignettes:1.
0": pull access denied, repository does not exist or may require authorization: authorization failed
: no basic auth credentials
```

Le même message qu'à l'exercice 3 : un Secret pour un autre serveur ne sert à
rien, et le kubelet tire comme s'il n'en avait aucun. La cause ne se voit que
dans le Secret. Son champ `.dockerconfigjson` est encodé en base64 :

```bash
kubectl get secret registre-essai -n essai-images -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d; echo
```

```text
{"auths":{"localhost:5000":{"username":"galerie","password":"Vignettes-2026","auth":"Z2FsZXJpZTpWaWduZXR0ZXMtMjAyNg=="}}}
```

`localhost:5000`, au lieu de `localhost:30500`. Corrigez le Secret **en
place**, sous le même nom : `--dry-run=client -o yaml` fabrique le nouveau
Secret, et `kubectl replace` remplace l'ancien. Attendez une minute, sans
toucher aux Pods :

```bash
kubectl create secret docker-registry registre-essai --docker-server=localhost:30500 --docker-username=galerie --docker-password=Vignettes-2026 -n essai-images --dry-run=client -o yaml | kubectl replace -f -
sleep 60; kubectl get pods -n essai-images -l app=miniatures -o custom-columns='POD:.metadata.name,PRET:.status.containerStatuses[0].ready,ETAT:.status.containerStatuses[0].state.waiting.reason,SECRETS:.spec.imagePullSecrets'
```

```text
secret/registre-essai replaced
POD                           PRET   ETAT     SECRETS
miniatures-666c6d7978-4nj7t   true   <none>   [map[name:registre-essai]]
```

Le Pod qui portait déjà le Secret a tiré son image tout seul, au tour suivant
de ses essais : le kubelet relit le **contenu** du Secret à chaque tentative.
L'ancien Pod, sans Secret, a disparu avec la fin du déploiement. Un Pod né
**avant** que le ServiceAccount ait son Secret ne le reçoit jamais : il faut le
remplacer. Le Deployment, lui, ne cite toujours aucun Secret :

```bash
kubectl rollout status deployment/miniatures -n essai-images --timeout=120s | tail -1
kubectl get deployment miniatures -n essai-images -o jsonpath='{.spec.template.spec.imagePullSecrets}'; echo '(fin)'
```

```text
deployment "miniatures" successfully rolled out
(fin)
```

Rien avant `(fin)` : c'est le ServiceAccount qui ajoute le Secret aux Pods.

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
