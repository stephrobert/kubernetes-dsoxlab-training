# Une base Kustomize et deux overlays

Une même application tourne souvent dans plusieurs environnements : test,
démonstration, production. Recopier ses manifestes pour chacun finit toujours
par des copies qui divergent. **Kustomize**, intégré à kubectl, part d'une
**base** commune et lui applique des **overlays** : de petits fichiers qui ne
décrivent que les différences. Dans ce cours, vous écrivez une base, vous voyez
le nom d'une ConfigMap générée changer avec son contenu, vous écrivez un
overlay, vous vérifiez qu'un label atteint bien le sélecteur du Service, vous
changez l'image dans un second overlay, vous appliquez les deux, puis vous
changez la configuration.

Vous travaillez avec une application `site` et deux environnements d'essai,
`essai-qualif` et `essai-demo`. Le challenge vous demandera une autre
application, dans `dev` et `prod` : vous le ferez seul, à la fin.

Page associée : [Kustomize](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kustomize/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-kustomize-overlays
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026, avec Kubernetes v1.37.2 et la version de Kustomize intégrée à
kubectl, v5.8.1.

## 📚 Exercice 1 : une base

Créez les deux namespaces d'essai et l'arborescence de travail : une base, et
un dossier par overlay :

```bash
kubectl create namespace essai-qualif; kubectl create namespace essai-demo; mkdir -p ~/essai-kustomize/base ~/essai-kustomize/overlays/qualif ~/essai-kustomize/overlays/demo
```

```text
namespace/essai-qualif created
namespace/essai-demo created
```

La base contient les manifestes ordinaires, **sans namespace**, et un fichier
`kustomization.yaml`. Celui-ci liste les manifestes dans `resources`, et
demande à Kustomize de **générer** une ConfigMap `site-config`
(`configMapGenerator`). Le Deployment lit cette ConfigMap par `envFrom` :

```bash
cd ~/essai-kustomize/base
cat > deployment.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: site
spec:
  replicas: 1
  selector:
    matchLabels:
      app: site
  template:
    metadata:
      labels:
        app: site
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          ports:
            - containerPort: 80
          envFrom:
            - configMapRef:
                name: site-config
YAML
cat > service.yaml <<'YAML'
apiVersion: v1
kind: Service
metadata:
  name: site-svc
spec:
  selector:
    app: site
  ports:
    - port: 80
      targetPort: 80
YAML
cat > kustomization.yaml <<'YAML'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
configMapGenerator:
  - name: site-config
    literals:
      - COULEUR=bleu
YAML
ls
```

```text
deployment.yaml
kustomization.yaml
service.yaml
```

`kubectl kustomize` affiche ce que Kustomize produit, **sans rien appliquer** :

```bash
kubectl kustomize ~/essai-kustomize/base
```

```text
apiVersion: v1
data:
  COULEUR: bleu
kind: ConfigMap
metadata:
  name: site-config-mgm6hf9htk
---
apiVersion: v1
kind: Service
metadata:
  name: site-svc
spec:
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: site
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: site
spec:
  replicas: 1
  selector:
    matchLabels:
      app: site
  template:
    metadata:
      labels:
        app: site
    spec:
      containers:
      - envFrom:
        - configMapRef:
            name: site-config-mgm6hf9htk
        image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
        name: nginx
        ports:
        - containerPort: 80
```

Trois objets séparés par `---`. La ConfigMap s'appelle
`site-config-mgm6hf9htk` : Kustomize a ajouté une **empreinte** de son
contenu. Il a aussi réécrit le nom dans l'`envFrom` du Deployment.

## 📚 Exercice 2 : le nom change avec le contenu

Relevez le nom de la ConfigMap générée, changez la couleur, puis relevez-le à
nouveau :

```bash
kubectl kustomize ~/essai-kustomize/base | grep -E '^  name: site-config|^                name: site-config'
sed -i 's/COULEUR=bleu/COULEUR=vert/' ~/essai-kustomize/base/kustomization.yaml; kubectl kustomize ~/essai-kustomize/base | grep -E '^  name: site-config'
```

```text
  name: site-config-mgm6hf9htk
  name: site-config-g7gd24m975
```

Un autre contenu donne un autre nom. Comme le Deployment cite ce nom, son modèle
de Pod change aussi : appliquer la nouvelle configuration redémarre ses Pods,
qui lisent alors la nouvelle valeur. Remettez la couleur d'origine, et
l'empreinte revient :

```bash
sed -i 's/COULEUR=vert/COULEUR=bleu/' ~/essai-kustomize/base/kustomization.yaml; kubectl kustomize ~/essai-kustomize/base | grep -E '^  name: site-config'
```

```text
  name: site-config-mgm6hf9htk
```

## 📚 Exercice 3 : un overlay qui ne porte que les différences

L'overlay `qualif` reprend la base (`resources: ../../base`), puis ne dit que
ce qui change : le namespace, un préfixe ajouté aux noms (`namePrefix`), un
label `env: qualif`, et le nombre de réplicas. `grep` ne garde que les lignes
qui portent ces changements :

```bash
cat > ~/essai-kustomize/overlays/qualif/kustomization.yaml <<'YAML'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
namespace: essai-qualif
namePrefix: qualif-
labels:
  - pairs:
      env: qualif
    includeSelectors: true
replicas:
  - name: site
    count: 1
YAML
kubectl kustomize ~/essai-kustomize/overlays/qualif | grep -E '^kind:|^  name:|^  namespace:|^    env:|^      env:|^        env:|name: qualif-site-config'
```

```text
kind: ConfigMap
    env: qualif
  name: qualif-site-config-mgm6hf9htk
  namespace: essai-qualif
kind: Service
    env: qualif
  name: qualif-site-svc
  namespace: essai-qualif
    env: qualif
kind: Deployment
    env: qualif
  name: qualif-site
  namespace: essai-qualif
      env: qualif
        env: qualif
            name: qualif-site-config-mgm6hf9htk
```

Chaque objet a reçu le préfixe `qualif-`, le namespace `essai-qualif` et le
label `env: qualif`. Le Service porte le label deux fois : sur lui-même, et
dans son sélecteur. Le Deployment le porte trois fois : sur lui-même, dans son
sélecteur, et sur le modèle de ses Pods. Le nom de la ConfigMap est réécrit
partout, préfixe compris. La base, elle, n'a pas changé.

## 📚 Exercice 4 : le label doit atteindre le sélecteur

`includeSelectors: true` demande à Kustomize de mettre le label aussi dans les
sélecteurs. Voyez ce qui se passe sans lui. Créez un overlay
`sans-selecteur`, copie de `qualif` avec `includeSelectors: false`, et
regardez le sélecteur de son Service :

```bash
mkdir -p ~/essai-kustomize/overlays/sans-selecteur; sed 's/includeSelectors: true/includeSelectors: false/' ~/essai-kustomize/overlays/qualif/kustomization.yaml > ~/essai-kustomize/overlays/sans-selecteur/kustomization.yaml; kubectl kustomize ~/essai-kustomize/overlays/sans-selecteur | sed -n '/^kind: Service/,/^---/p' | grep -A3 'selector:'
```

```text
  selector:
    app: site
---
```

Le sélecteur ne cite que `app: site`. Si deux environnements partageaient un
namespace, ce Service trouverait les Pods des deux. Avec `qualif` :

```bash
kubectl kustomize ~/essai-kustomize/overlays/qualif | sed -n '/^kind: Service/,/^---/p' | grep -A3 'selector:'
```

```text
  selector:
    app: site
    env: qualif
---
```

Le Service ne trouve que les Pods de son environnement.

## 📚 Exercice 5 : un second overlay qui change l'image

L'overlay `demo` fait la même chose avec 2 réplicas, et passe l'image en
version 1.30.6 par un bloc `images`. Celui-ci vise les images nommées `nginx`
et leur donne un nouveau tag et un nouveau digest :

```bash
cat > ~/essai-kustomize/overlays/demo/kustomization.yaml <<'YAML'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
namespace: essai-demo
namePrefix: demo-
labels:
  - pairs:
      env: demo
    includeSelectors: true
replicas:
  - name: site
    count: 2
images:
  - name: nginx
    newTag: 1.30.6
    digest: sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
YAML
kubectl kustomize ~/essai-kustomize/overlays/demo | grep -E 'image:|replicas:'
```

```text
  replicas: 2
        image: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
```

La base, elle, décrit toujours la version 1.30.5 et 1 réplica :

```bash
kubectl kustomize ~/essai-kustomize/base | grep -E 'image:|replicas:'
```

```text
  replicas: 1
        image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

Un changement propre à un environnement va dans son overlay, jamais dans la
base.

## 📚 Exercice 6 : appliquer et vérifier

`kubectl apply -k` applique un dossier Kustomize. Appliquez les deux overlays,
puis attendez les deux déploiements :

```bash
kubectl apply -k ~/essai-kustomize/overlays/qualif; kubectl apply -k ~/essai-kustomize/overlays/demo
kubectl rollout status deployment/qualif-site -n essai-qualif --timeout=180s | tail -1; kubectl rollout status deployment/demo-site -n essai-demo --timeout=180s | tail -1
```

```text
configmap/qualif-site-config-mgm6hf9htk created
service/qualif-site-svc created
deployment.apps/qualif-site created
configmap/demo-site-config-mgm6hf9htk created
service/demo-site-svc created
deployment.apps/demo-site created
deployment "qualif-site" successfully rolled out
deployment "demo-site" successfully rolled out
```

Regardez ce que contient `essai-demo` :

```bash
kubectl get deploy,svc,configmap -n essai-demo
```

```text
NAME                        READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/demo-site   2/2     2            2           1s

NAME                    TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
service/demo-site-svc   ClusterIP   10.99.212.73   <none>        80/TCP    1s

NAME                                    DATA   AGE
configmap/demo-site-config-mgm6hf9htk   1      1s
configmap/kube-root-ca.crt              1      2s
```

Les Pods portent leur label d'environnement (`-L env` ajoute la colonne, et
`awk` ne garde que cinq colonnes) :

```bash
kubectl get pods -n essai-demo -L env -o wide | awk '{print $1, $2, $3, $6, $NF}' | column -t
```

```text
NAME                       READY  STATUS   IP             ENV
demo-site-b668c76c4-22529  1/1    Running  10.244.163.42  demo
demo-site-b668c76c4-g5q5q  1/1    Running  10.244.38.124  demo
```

Le Service trouve les deux Pods, et le conteneur a reçu sa configuration :

```bash
kubectl get endpointslices -n essai-demo -l kubernetes.io/service-name=demo-site-svc -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]}{"\n"}{end}'
kubectl exec -n essai-demo deploy/demo-site -- printenv COULEUR
```

```text
10.244.38.124
10.244.163.42
bleu
```

Enfin, `kubectl diff -k` compare chaque overlay au cluster :

```bash
kubectl diff -k ~/essai-kustomize/overlays/qualif > /dev/null; echo "qualif : code $?"; kubectl diff -k ~/essai-kustomize/overlays/demo > /dev/null; echo "demo : code $?"
```

```text
qualif : code 0
demo : code 0
```

Code 0 : le cluster correspond au dossier.

## 📚 Exercice 7 : changer la configuration redémarre les Pods

Changez la couleur dans la base, puis réappliquez l'overlay `demo` :

```bash
sed -i 's/COULEUR=bleu/COULEUR=vert/' ~/essai-kustomize/base/kustomization.yaml; kubectl apply -k ~/essai-kustomize/overlays/demo
```

```text
configmap/demo-site-config-g7gd24m975 created
service/demo-site-svc unchanged
deployment.apps/demo-site configured
```

Une **nouvelle** ConfigMap est créée, et le Deployment est modifié pour la
citer. Ses Pods sont donc remplacés :

```bash
kubectl rollout status deployment/demo-site -n essai-demo --timeout=180s | tail -1; kubectl exec -n essai-demo deploy/demo-site -- printenv COULEUR
```

```text
deployment "demo-site" successfully rolled out
vert
```

Les nouveaux Pods lisent `vert`. L'ancienne ConfigMap, elle, est toujours là :

```bash
kubectl get configmap -n essai-demo
```

```text
NAME                          DATA   AGE
demo-site-config-g7gd24m975   1      2s
demo-site-config-mgm6hf9htk   1      3s
kube-root-ca.crt              1      4s
```

`apply` ne supprime rien de lui-même. C'est plutôt utile : un retour arrière
retrouve l'ancienne configuration intacte.

## 🧹 Nettoyage

Supprimez les deux namespaces d'essai et l'arborescence de travail :

```bash
kubectl delete namespace essai-qualif essai-demo; rm -rf ~/essai-kustomize
```

```text
namespace "essai-qualif" deleted
namespace "essai-demo" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-kustomize-overlays
dsoxlab check ckad-kustomize-overlays
```

```text
╭─ Résultat : ckad-kustomize-overlays ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/9 tests     │
╰──────────────────────────────────────╯
```

0 sur 9 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une autre application, une base et deux overlays,
`dev` et `prod`, dont un seul passe en version 2.

```bash
dsoxlab run ckad-kustomize-overlays
dsoxlab challenge ckad-kustomize-overlays
```
