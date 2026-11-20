# Prévisualiser avec diff, attendre avec wait

Avant d'appliquer un changement, on veut savoir ce qu'il va modifier. Après
l'avoir appliqué, on veut savoir quand il est vraiment fini. `kubectl diff`
répond à la première question, `kubectl rollout status` et `kubectl wait` à la
seconde. La leçon les présente et assemble un script de déploiement. Ce cours
part de ce qui tourne mal : un déploiement bloqué qu'on annule, un dossier qui
ne dit plus ce que fait le cluster, un Job qui échoue sans que l'attente le
voie, des Jobs à attendre dans un dossier, et un `apply` qui s'arrête à
moitié.

Vous travaillez dans un namespace d'essai, `essai-attente`, avec un Deployment
`accueil` et deux Jobs d'essai. Un **Job** lance un Pod qui fait une tâche,
puis s'arrête : la leçon sur les Jobs les détaille plus loin dans la
formation. Le challenge vous demandera un script de déploiement complet, sur
une autre application : vous l'écrirez seul, à la fin.

Page associée : [kubectl wait et diff](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-wait-diff/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-verifier-et-attendre
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`lab` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026, avec Kubernetes v1.37.0.

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

## 📚 Exercice 1 : rappel, les codes de diff et set -e

La leçon détaille les trois codes de sortie de `kubectl diff`. Revoyez-les
d'un coup. Passez l'image du fichier à une version qui **n'existe pas**,
`nginx:1.30.6-introuvable`, puis comparez le dossier, et enfin un fichier
absent. `grep` ne garde que les lignes modifiées, et `${PIPESTATUS[0]}` donne
le code de `kubectl diff`, et non celui de `grep` :

```bash
kubectl diff -f ~/essai-attente/; echo "code $?"
sed -i 's/image: nginx:1.30.5@sha256:[0-9a-f]*/image: nginx:1.30.6-introuvable/' ~/essai-attente/accueil.yaml; kubectl diff -f ~/essai-attente/ | grep -E '^[-+] '; echo "code ${PIPESTATUS[0]}"
kubectl diff -f ~/essai-attente/introuvable.yaml; echo "code $?"
```

```text
code 0
-  generation: 1
+  generation: 2
-      - image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
+      - image: nginx:1.30.6-introuvable
code 1
error: the path "/home/ansible/essai-attente/introuvable.yaml" does not exist
code 2
```

0 : aucune différence. 1 : des différences, ce qui n'est pas une erreur. 2 :
kubectl n'a pas pu comparer. Sous `set -e`, qui arrête un script à la première
commande en échec, le code 1 arrête tout au moment même où il faudrait
appliquer. `|| code=$?` garde le code sans arrêter le script :

```bash
bash -c 'set -e; kubectl diff -f ~/essai-attente/ > /dev/null; echo "je continue"'; echo "code $?"
bash -c 'set -e; code=0; kubectl diff -f ~/essai-attente/ > /dev/null || code=$?; echo "diff a rendu $code"'
```

```text
code 1
diff a rendu 1
```

## 📚 Exercice 2 : un déploiement bloqué, puis annulé

Appliquez le fichier, qui demande maintenant l'image introuvable, et attendez
la fin du déploiement avec un délai de 30 secondes :

```bash
kubectl apply -f ~/essai-attente/accueil.yaml; kubectl rollout status deployment/accueil -n essai-attente --timeout=30s; echo "code $?"
kubectl get pods -n essai-attente -l app=accueil
```

```text
deployment.apps/accueil configured
Waiting for deployment "accueil" rollout to finish: 1 out of 3 new replicas have been updated...
error: timed out waiting for the condition
code 1
NAME                      READY   STATUS             RESTARTS   AGE
accueil-5c6db657b-2kznd   1/1     Running            0          42s
accueil-5c6db657b-5ksz9   1/1     Running            0          42s
accueil-5c6db657b-qjnwb   1/1     Running            0          42s
accueil-db88c9bcd-6s4vp   0/1     ImagePullBackOff   0          31s
```

`rollout status` rend la main au bout du délai, avec le code 1 : le
déploiement n'a pas fini. Le nouveau Pod ne trouve pas son image
(`ImagePullBackOff`), et les trois anciens continuent de servir. Dans un
script, c'est ce code 1 qui doit arrêter la suite. Revenez à la version
précédente avec `rollout undo` :

```bash
kubectl rollout undo deployment/accueil -n essai-attente; kubectl rollout status deployment/accueil -n essai-attente --timeout=120s | tail -1
kubectl get deployment accueil -n essai-attente -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

```text
Warning: resource deployments/accueil was previously managed with 'kubectl apply'. Rolling back will not update the kubectl.kubernetes.io/last-applied-configuration annotation, which may cause unexpected behavior on future 'kubectl apply' operations. Consider using 'kubectl apply' with your previous configuration file instead.
deployment.apps/accueil rolled back
deployment "accueil" successfully rolled out
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

Le cluster est revenu en 1.30.5. L'avertissement le dit : `undo` ne touche
pas au fichier. Comparez le dossier au cluster :

```bash
kubectl diff -f ~/essai-attente/ | grep -E '^[-+] .*image'; echo "code ${PIPESTATUS[0]}"
```

```text
-      - image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
+      - image: nginx:1.30.6-introuvable
code 1
```

`diff` rend de nouveau 1 : le dossier demande toujours l'image introuvable, et
le prochain `apply` relancerait la même panne. Après un `undo`, corrigez aussi
le fichier :

```bash
sed -i 's/image: nginx:1.30.6-introuvable/image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb/' ~/essai-attente/accueil.yaml; kubectl diff -f ~/essai-attente/ > /dev/null; echo "code $?"
```

```text
code 0
```

## 📚 Exercice 3 : un Job qui échoue

Écrivez deux Jobs dans un sous-dossier `taches` : `vider-cache` travaille 6
secondes puis réussit, `tache-ratee` échoue tout de suite (`exit 3`).
`backoffLimit: 0` interdit de relancer un Pod en échec :

```bash
mkdir -p ~/essai-attente/taches
cat > ~/essai-attente/taches/vider-cache.yaml <<'YAML'
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
cat > ~/essai-attente/taches/tache-ratee.yaml <<'YAML'
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
kubectl apply -f ~/essai-attente/taches/
```

```text
job.batch/tache-ratee created
job.batch/vider-cache created
```

Attendez la réussite de `tache-ratee`, puis son échec. `time` mesure la durée
de chaque commande (ligne `real`) :

```bash
time kubectl wait --for=condition=Complete job/tache-ratee -n essai-attente --timeout=15s
time kubectl wait --for=condition=Failed job/tache-ratee -n essai-attente --timeout=15s
```

```text
error: timed out waiting for the condition on jobs/tache-ratee

real	0m15.051s
user	0m0.026s
sys	0m0.017s
job.batch/tache-ratee condition met

real	0m0.159s
user	0m0.031s
sys	0m0.005s
```

`Complete` a attendu les 15 secondes pour rien : un Job en échec ne la remplit
jamais. `Failed` répond tout de suite. Avec un délai de 300 secondes dans un
pipeline, attendre la seule réussite fait perdre cinq minutes avant de savoir.

## 📚 Exercice 4 : attendre tous les Jobs d'un dossier

Un script de déploiement ne connaît pas d'avance les objets d'un dossier :
`kubectl get -f` les liste. Essayez avec `-o name`, puis attendez le premier
Job ainsi trouvé :

```bash
kubectl get -f ~/essai-attente/taches/ -o name
kubectl wait --for=condition=Complete job/vider-cache --timeout=0
```

```text
job.batch/tache-ratee
job.batch/vider-cache
Error from server (NotFound): jobs.batch "vider-cache" not found
```

Le Job existe pourtant. `-o name` ne donne pas le namespace, et `wait` a
cherché dans celui du contexte, `default`. Demandez aussi le namespace, avec
`custom-columns` et sans ligne de titres. Essayez sur le dossier, puis sur un
seul fichier :

```bash
kubectl get -f ~/essai-attente/taches/ -o custom-columns=KIND:.kind,NS:.metadata.namespace,NOM:.metadata.name --no-headers
kubectl get -f ~/essai-attente/taches/vider-cache.yaml -o custom-columns=KIND:.kind,NS:.metadata.namespace,NOM:.metadata.name --no-headers
```

```text
Job   essai-attente   tache-ratee
Job   essai-attente   vider-cache
Job   essai-attente   vider-cache
```

Une ligne par objet, dans les deux cas. Avec un seul objet, `kubectl get` ne
rend pas une liste : un JSONPath qui parcourt `.items` ne trouverait alors
rien, alors que `custom-columns` marche toujours.

Écrivez un script qui lit ces lignes, et qui, pour chaque Job, interroge
`Complete` puis `Failed` à tour de rôle avec `--timeout=0` (une seule
vérification, sans attendre), dans une boucle bornée à 60 secondes. Il sort en
erreur au premier Job qui échoue :

```bash
cat > ~/essai-attente/attendre-jobs.sh <<'EOF'
#!/usr/bin/env bash
# Usage : ./attendre-jobs.sh <dossier> : attend chaque Job du dossier, et sort
# en erreur au premier qui échoue.
set -euo pipefail
while read -r kind ns nom; do
  [ "$kind" = Job ] || continue
  fin=$((SECONDS + 60)); etat=2
  while [ "$SECONDS" -lt "$fin" ]; do
    if kubectl wait --for=condition=Complete "job/$nom" -n "$ns" --timeout=0 >/dev/null 2>&1; then etat=0; break; fi
    if kubectl wait --for=condition=Failed "job/$nom" -n "$ns" --timeout=0 >/dev/null 2>&1; then etat=1; break; fi
    sleep 2
  done
  echo "job/$nom : code $etat"
  [ "$etat" -eq 0 ] || exit 1
done < <(kubectl get -f "$1" -o custom-columns=KIND:.kind,NS:.metadata.namespace,NOM:.metadata.name --no-headers)
echo "Tous les Jobs sont terminés."
EOF
chmod +x ~/essai-attente/attendre-jobs.sh
time ~/essai-attente/attendre-jobs.sh ~/essai-attente/taches/; echo "code $?"
```

```text
job/tache-ratee : code 1

real	0m0.118s
user	0m0.078s
sys	0m0.029s
code 1
```

Le script voit l'échec de `tache-ratee` au premier tour, et sort en erreur
aussitôt. `[ "$kind" = Job ] || continue` passe les objets qui ne sont pas des
Jobs, et `< <(...)` donne à la boucle la sortie de `kubectl get`. Retirez le
Job raté du dossier, et relancez :

```bash
rm ~/essai-attente/taches/tache-ratee.yaml; ~/essai-attente/attendre-jobs.sh ~/essai-attente/taches/; echo "code $?"
```

```text
job/vider-cache : code 0
Tous les Jobs sont terminés.
code 0
```

## 📚 Exercice 5 : un dossier dont un objet est refusé

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
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests      │
╰───────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : passer une autre application en version 2, attendre
la vraie fin du déploiement et d'un Job, relever la révision atteinte, et
écrire un script de déploiement qui sait s'arrêter, y compris quand un Job
échoue.

```bash
dsoxlab run k8s-verifier-et-attendre
dsoxlab challenge k8s-verifier-et-attendre
```
