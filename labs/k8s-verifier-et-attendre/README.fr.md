# Prévisualiser avec diff, attendre avec wait

Avant d'appliquer un changement, on veut savoir ce qu'il va modifier. Après
l'avoir appliqué, on veut savoir quand il est vraiment fini. `kubectl diff`
répond à la première question, `kubectl rollout status` et `kubectl wait` à la
seconde. Dans ce cours, vous mesurez les codes de sortie de `kubectl diff`,
vous voyez le piège qu'ils tendent à un script, vous distinguez un déploiement
disponible d'un déploiement terminé, vous attendez la fin d'un Job qui réussit
puis d'un Job qui échoue, et vous voyez ce que fait `apply` quand un objet du
dossier est refusé.

Vous travaillez dans un namespace d'essai, `essai-attente`, avec un Deployment
`accueil` et deux Jobs d'essai. Le challenge vous demandera la même chose sur
une autre application : vous le ferez seul, à la fin.

Page associée : [kubectl wait et diff](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-wait-diff/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-verifier-et-attendre
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`lab` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026, avec Kubernetes 1.37.

Préparez le namespace d'essai et un dossier qui contient le Deployment
`accueil` : 3 Pods nginx en version 1.30.5, avec une sonde de disponibilité.
Appliquez-le et attendez qu'il soit prêt :

```bash
kubectl create namespace essai-attente; mkdir -p ~/essai-attente
cat > ~/essai-attente/accueil.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: accueil
  namespace: essai-attente
spec:
  replicas: 3
  selector:
    matchLabels:
      app: accueil
  template:
    metadata:
      labels:
        app: accueil
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
YAML
kubectl apply -f ~/essai-attente/accueil.yaml && kubectl rollout status deployment/accueil -n essai-attente --timeout=180s | tail -1
```

```text
namespace/essai-attente created
deployment.apps/accueil created
deployment "accueil" successfully rolled out
```

## 📚 Exercice 1 : les trois codes de kubectl diff

`kubectl diff` compare un fichier ou un dossier à ce qui tourne dans le
cluster. Son **code de sortie** (que le shell range dans `$?`) dit ce qu'il a
trouvé. Comparez le dossier tel quel :

```bash
kubectl diff -f ~/essai-attente/; echo "code $?"
```

```text
code 0
```

Aucune différence : rien ne s'affiche, et le code vaut 0. Passez maintenant
l'image du fichier en version 1.30.6, puis comparez à nouveau. `grep` ne garde
que les lignes modifiées, et `${PIPESTATUS[0]}` donne le code de `kubectl diff`
(et non celui de `grep`) :

```bash
sed -i 's/nginx:1.30.5@sha256:[0-9a-f]*/nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703/' ~/essai-attente/accueil.yaml; kubectl diff -f ~/essai-attente/ | grep -E '^[-+] '; echo "code ${PIPESTATUS[0]}"
```

```text
-  generation: 1
+  generation: 2
-      - image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
+      - image: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
code 1
```

Le `-` montre ce qui tourne, le `+` ce que donnerait `apply`. Le code vaut 1.
Enfin, demandez une comparaison impossible, sur un fichier qui n'existe pas :

```bash
kubectl diff -f ~/essai-attente/introuvable.yaml; echo "code $?"
```

```text
error: the path "/home/ansible/essai-attente/introuvable.yaml" does not exist
code 2
```

Les trois cas :

- **0** : aucune différence ;
- **1** : des différences, ce qui n'est **pas** une erreur ;
- **2** (ou plus) : kubectl n'a pas pu comparer, c'est une vraie erreur.

## 📚 Exercice 2 : diff sous set -e

Un script commence souvent par `set -e` : il s'arrête dès qu'une commande sort
avec un code différent de 0. Voyez ce qui arrive avec `kubectl diff`, alors
qu'il y a des différences dans le dossier :

```bash
bash -c 'set -e; kubectl diff -f ~/essai-attente/ > /dev/null; echo "je continue"'; echo "code $?"
```

```text
code 1
```

Le script s'arrête avant `je continue`, au moment même où il fallait
appliquer. Pour `set -e`, le code 1 de `diff` est un échec. La parade : garder
le code dans une variable. `|| code=$?` ne s'exécute que si `diff` sort en
erreur, et `set -e` ne s'arrête pas sur une commande suivie de `||` :

```bash
bash -c 'set -e; code=0; kubectl diff -f ~/essai-attente/ > /dev/null || code=$?; echo "diff a rendu $code"'
```

```text
diff a rendu 1
```

Le script continue et connaît le code : 0, rien à faire ; 1, il faut
appliquer ; 2 ou plus, il faut s'arrêter.

## 📚 Exercice 3 : disponible n'est pas terminé

Appliquez le changement d'image, puis attendez que le Deployment soit
**Available** (disponible), et regardez aussitôt ses Pods. Les colonnes
donnent le nom du Pod, s'il est prêt, s'il est en cours d'arrêt (`ARRET`), et
le début de son image :

```bash
kubectl apply -f ~/essai-attente/accueil.yaml && kubectl wait --for=condition=Available deployment/accueil -n essai-attente --timeout=60s && kubectl get pods -n essai-attente -l app=accueil -o custom-columns='POD:.metadata.name,PRET:.status.containerStatuses[0].ready,ARRET:.metadata.deletionTimestamp,IMAGE:.spec.containers[0].image' | cut -c1-82
```

```text
deployment.apps/accueil configured
deployment.apps/accueil condition met
POD                        PRET    ARRET    IMAGE
accueil-5c6db657b-hjpjh    true    <none>   nginx:1.30.5@sha256:9bf97bd7714f5e24c1
accueil-5c6db657b-qr7q2    true    <none>   nginx:1.30.5@sha256:9bf97bd7714f5e24c1
accueil-5c6db657b-vpwpn    true    <none>   nginx:1.30.5@sha256:9bf97bd7714f5e24c1
accueil-5cbc7d7b69-mnpwg   false   <none>   nginx:1.30.6@sha256:42c68eab6f7e226117
```

`wait` a rendu la main tout de suite. Pourtant, les trois Pods en 1.30.5
servent encore, et le seul Pod en 1.30.6 n'est pas prêt. **Available** veut
dire « assez de Pods prêts pour servir », pas « mise à jour finie ».

`kubectl rollout status` attend, lui, que tous les Pods soient remplacés :

```bash
kubectl rollout status deployment/accueil -n essai-attente --timeout=180s
```

```text
Waiting for deployment "accueil" rollout to finish: 1 out of 3 new replicas have been updated...
Waiting for deployment "accueil" rollout to finish: 1 out of 3 new replicas have been updated...
Waiting for deployment "accueil" rollout to finish: 1 out of 3 new replicas have been updated...
Waiting for deployment "accueil" rollout to finish: 2 out of 3 new replicas have been updated...
Waiting for deployment "accueil" rollout to finish: 2 out of 3 new replicas have been updated...
Waiting for deployment "accueil" rollout to finish: 2 out of 3 new replicas have been updated...
Waiting for deployment "accueil" rollout to finish: 2 out of 3 new replicas have been updated...
Waiting for deployment "accueil" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "accueil" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "accueil" rollout to finish: 1 old replicas are pending termination...
deployment "accueil" successfully rolled out
```

Regardez de nouveau les Pods :

```bash
kubectl get pods -n essai-attente -l app=accueil -o custom-columns='POD:.metadata.name,PRET:.status.containerStatuses[0].ready,ARRET:.metadata.deletionTimestamp,IMAGE:.spec.containers[0].image' | cut -c1-82
```

```text
POD                        PRET   ARRET                  IMAGE
accueil-5c6db657b-vpwpn    true   2026-11-19T19:31:01Z   nginx:1.30.5@sha256:9bf97
accueil-5cbc7d7b69-844tt   true   <none>                 nginx:1.30.6@sha256:42c68
accueil-5cbc7d7b69-mnpwg   true   <none>                 nginx:1.30.6@sha256:42c68
accueil-5cbc7d7b69-v8nm9   true   <none>                 nginx:1.30.6@sha256:42c68
```

Les trois Pods en 1.30.6 sont prêts. Le dernier Pod en 1.30.5 porte une date
dans `ARRET` : il est en train de s'arrêter, et ne fait déjà plus partie du
Deployment. Le dossier et le cluster disent maintenant la même chose :

```bash
kubectl diff -f ~/essai-attente/; echo "code $?"
```

```text
code 0
```

## 📚 Exercice 4 : attendre la fin d'un Job

Un **Job** lance un Pod qui fait une tâche, puis s'arrête. Lancez un Job qui
travaille 6 secondes :

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: vider-cache
  namespace: essai-attente
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: vider
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "echo cache en cours de vidage; sleep 6; echo cache vide"]
YAML
```

```text
job.batch/vider-cache created
```

`kubectl wait --for=condition=complete` attend que le Job soit terminé avec
succès. `time` mesure combien de temps la commande a duré (ligne `real`) :

```bash
time kubectl wait --for=condition=complete job/vider-cache -n essai-attente --timeout=60s
kubectl logs job/vider-cache -n essai-attente
```

```text
job.batch/vider-cache condition met

real	0m8.812s
user	0m0.030s
sys	0m0.008s
cache en cours de vidage
cache vide
```

`wait` a rendu la main au bout de 9 secondes environ, quand le Job a fini. Ses
journaux le confirment.

## 📚 Exercice 5 : un Job qui échoue

Lancez un Job qui échoue tout de suite (`exit 3`). `backoffLimit: 0` interdit
de le relancer :

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: tache-ratee
  namespace: essai-attente
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: tache
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "echo echec volontaire; exit 3"]
YAML
```

```text
job.batch/tache-ratee created
```

Attendez sa réussite, comme pour le Job précédent :

```bash
time kubectl wait --for=condition=complete job/tache-ratee -n essai-attente --timeout=20s
```

```text
error: timed out waiting for the condition on jobs/tache-ratee

real	0m20.037s
user	0m0.026s
sys	0m0.009s
```

`wait` a attendu les 20 secondes du `--timeout` pour rien : un Job en échec ne
sera jamais `complete`. Sans `--timeout`, il aurait attendu 30 secondes, la
valeur par défaut, et bien plus longtemps avec un `--timeout` plus grand.
Attendez plutôt la condition **failed** :

```bash
time kubectl wait --for=condition=failed job/tache-ratee -n essai-attente --timeout=20s
kubectl get job tache-ratee -n essai-attente
```

```text
job.batch/tache-ratee condition met

real	0m0.137s
user	0m0.025s
sys	0m0.011s
NAME          STATUS   COMPLETIONS   DURATION   AGE
tache-ratee   Failed   0/1           20s        20s
```

Réponse immédiate : le Job est en échec. Pour ne pas rester bloqué, on attend
toujours avec un `--timeout`, et on surveille aussi la condition `failed`.

## 📚 Exercice 6 : un dossier dont un objet est refusé

Préparez un dossier `lot` avec deux fichiers : une ConfigMap correcte, et un
Deployment `casse` dont le sélecteur (`app: casse`) ne correspond pas aux
labels de ses Pods (`app: autre-chose`). Comparez-le au cluster :

```bash
mkdir -p ~/essai-attente/lot
cat > ~/essai-attente/lot/a-reglages.yaml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: reglages-accueil
  namespace: essai-attente
data:
  THEME: clair
YAML
cat > ~/essai-attente/lot/b-casse.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: casse
  namespace: essai-attente
spec:
  replicas: 1
  selector:
    matchLabels:
      app: casse
  template:
    metadata:
      labels:
        app: autre-chose
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
YAML
kubectl diff -f ~/essai-attente/lot/ > /dev/null; echo "diff : code $?"
```

```text
The Deployment "casse" is invalid: spec.template.metadata.labels: Invalid value: {"app":"autre-chose"}: `selector` does not match template `labels`
diff : code 2
```

`diff` ne peut pas comparer un objet que le serveur refuse : code 2. Voyez ce
que fait `apply` sur le même dossier :

```bash
kubectl apply -f ~/essai-attente/lot/; echo "apply : code $?"
kubectl get configmap reglages-accueil -n essai-attente; kubectl get deployment casse -n essai-attente
```

```text
configmap/reglages-accueil created
The Deployment "casse" is invalid: spec.template.metadata.labels: Invalid value: {"app":"autre-chose"}: `selector` does not match template `labels`
apply : code 1
NAME               DATA   AGE
reglages-accueil   1      0s
Error from server (NotFound): deployments.apps "casse" not found
```

`apply` sort en erreur, mais il a **quand même** créé la ConfigMap. Le
cluster est maintenant à moitié modifié. C'est pour cela qu'un script de
déploiement compare d'abord, et s'arrête sans rien appliquer quand `diff` rend
2 ou plus.

## 🧹 Nettoyage

Supprimez le namespace d'essai et le dossier de travail :

```bash
kubectl delete namespace essai-attente; rm -rf ~/essai-attente
```

```text
namespace "essai-attente" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-verifier-et-attendre
dsoxlab check k8s-verifier-et-attendre
```

```text
╭─ Résultat : k8s-verifier-et-attendre ─╮
│  0 / 100 pts                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests      │
╰───────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : passer une autre application en version 2, attendre
la vraie fin du déploiement et d'un Job, relever les codes de `kubectl diff`,
et écrire un petit script de déploiement qui sait s'arrêter.

```bash
dsoxlab run k8s-verifier-et-attendre
dsoxlab challenge k8s-verifier-et-attendre
```
