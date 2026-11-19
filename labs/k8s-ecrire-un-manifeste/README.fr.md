# Écrire et valider un manifeste

Un **manifeste** est un fichier YAML qui décrit des objets Kubernetes. On le
garde dans un dépôt Git, et on le rejoue autant de fois que nécessaire. Dans ce
cours, vous faites générer un squelette par kubectl, vous voyez où va un objet
sans namespace, vous réunissez trois objets dans un seul fichier, vous le
faites valider par le serveur, vous l'appliquez, vous regardez l'écart avant
une modification, puis vous corrigez un objet existant sans le recréer.

Vous travaillez dans un namespace d'essai, `essai-manifeste`, avec une
application `annuaire`. Le challenge vous demandera une autre application, dans
un autre namespace : vous le ferez seul, à la fin.

Page associée : [Écrire des Manifests](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/ecrire-manifests/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-ecrire-un-manifeste
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`lab` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026, avec Kubernetes 1.37.

## 📚 Exercice 1 : générer un squelette

Créez le namespace d'essai et un répertoire de travail :

```bash
kubectl create namespace essai-manifeste; mkdir -p ~/essai-manifeste
```

```text
namespace/essai-manifeste created
```

Ne partez pas d'une page blanche. `kubectl create` accepte
`--dry-run=client` : kubectl prépare l'objet **sans l'envoyer** au cluster, et
`-o yaml` l'affiche en YAML :

```bash
kubectl create deployment annuaire --image=nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703 --replicas=2 --port=80 --dry-run=client -o yaml
```

```text
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: annuaire
  name: annuaire
spec:
  replicas: 2
  selector:
    matchLabels:
      app: annuaire
  strategy: {}
  template:
    metadata:
      labels:
        app: annuaire
    spec:
      containers:
      - image: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
        name: nginx
        ports:
        - containerPort: 80
        resources: {}
status: {}
```

Tout y est : le label `app: annuaire`, le sélecteur qui le reprend, le modèle de
Pod. Les lignes `{}` sont vides et peuvent être retirées. Vérifiez que rien n'a
été créé :

```bash
kubectl get deployment -n essai-manifeste
```

```text
No resources found in essai-manifeste namespace.
```

## 📚 Exercice 2 : les autres squelettes

La même méthode marche pour une ConfigMap :

```bash
kubectl create configmap annuaire-config --from-literal=LANGUE=fr --dry-run=client -o yaml
```

```text
apiVersion: v1
data:
  LANGUE: fr
kind: ConfigMap
metadata:
  name: annuaire-config
```

Et pour un Service. `--tcp=80:80` veut dire « port 80 du Service vers le port
80 des Pods » :

```bash
kubectl create service clusterip annuaire --tcp=80:80 --dry-run=client -o yaml
```

```text
apiVersion: v1
kind: Service
metadata:
  labels:
    app: annuaire
  name: annuaire
spec:
  ports:
  - name: 80-80
    port: 80
    protocol: TCP
    targetPort: 80
  selector:
    app: annuaire
  type: ClusterIP
status:
  loadBalancer: {}
```

Le sélecteur `app: annuaire` est déduit du nom du Service. Il trouve donc les
Pods du Deployment de l'exercice 1, qui portent le même label.

## 📚 Exercice 3 : sans namespace, l'objet va dans le contexte courant

Aucun des squelettes ne porte de namespace. Regardez celui de votre contexte
courant (`echo '(fin)'` marque la fin de la sortie) :

```bash
kubectl config view --minify -o jsonpath='{..namespace}'; echo '(fin)'
```

```text
(fin)
```

Rien avant `(fin)` : le contexte ne fixe aucun namespace, donc kubectl utilise
`default`. Créez un objet sans préciser de namespace, puis cherchez-le dans
tout le cluster :

```bash
kubectl create configmap essai-perdu --from-literal=a=1
kubectl get configmap -A | grep -E 'NAMESPACE|essai-perdu'
```

```text
configmap/essai-perdu created
NAMESPACE            NAME                                                   DATA   AGE
default              essai-perdu                                            1      0s
```

Il est dans `default`. Un manifeste qui ne nomme pas son namespace atterrit là
où pointe le contexte de celui qui l'applique, et ce n'est pas toujours le bon.
Supprimez-le :

```bash
kubectl delete configmap essai-perdu
```

```text
configmap "essai-perdu" deleted from default namespace
```

## 📚 Exercice 4 : un fichier, trois objets, un namespace

Un fichier peut porter plusieurs objets, séparés par une ligne `---`. Écrivez
le manifeste de l'application, à partir des trois squelettes. Chaque objet
nomme son namespace dans `metadata.namespace`. Le Deployment reçoit aussi la
ConfigMap dans ses variables d'environnement, avec `envFrom` :

```bash
cat > ~/essai-manifeste/annuaire.yaml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: annuaire-config
  namespace: essai-manifeste
data:
  LANGUE: fr
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: annuaire
  namespace: essai-manifeste
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
        - name: nginx
          image: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
          ports:
            - containerPort: 80
          envFrom:
            - configMapRef:
                name: annuaire-config
---
apiVersion: v1
kind: Service
metadata:
  name: annuaire
  namespace: essai-manifeste
spec:
  selector:
    app: annuaire
  ports:
    - port: 80
      targetPort: 80
YAML
grep -c '^---' ~/essai-manifeste/annuaire.yaml
```

```text
2
```

Deux séparateurs, donc trois objets.

## 📚 Exercice 5 : valider côté client, puis côté serveur

Fabriquez une copie fautive du fichier : `sed` ajoute au conteneur un
`imagePullPolicy` dont la valeur n'existe pas (`Parfois`) :

```bash
sed 's/^          ports:/          imagePullPolicy: Parfois\n          ports:/' ~/essai-manifeste/annuaire.yaml > ~/essai-manifeste/faux.yaml; grep -n imagePullPolicy ~/essai-manifeste/faux.yaml
```

```text
27:          imagePullPolicy: Parfois
```

Faites-la valider par kubectl seul, sans le serveur :

```bash
kubectl apply -f ~/essai-manifeste/faux.yaml --dry-run=client
```

```text
configmap/annuaire-config created (dry run)
deployment.apps/annuaire created (dry run)
service/annuaire created (dry run)
```

kubectl ne voit rien. Demandez maintenant au **serveur** de valider, toujours
sans rien créer :

```bash
kubectl apply -f ~/essai-manifeste/faux.yaml --dry-run=server
```

```text
configmap/annuaire-config created (server dry run)
service/annuaire created (server dry run)
The Deployment "annuaire" is invalid: spec.template.spec.containers[0].imagePullPolicy: Unsupported value: "Parfois": supported values: "Always", "IfNotPresent", "Never"
```

Le serveur refuse le Deployment, nomme le champ fautif et donne les valeurs
acceptées. Seul `--dry-run=server` passe le fichier aux mêmes contrôles qu'un
vrai `apply`. Le fichier correct, lui, passe :

```bash
kubectl apply -f ~/essai-manifeste/annuaire.yaml --dry-run=server
```

```text
configmap/annuaire-config created (server dry run)
deployment.apps/annuaire created (server dry run)
service/annuaire created (server dry run)
```

## 📚 Exercice 6 : appliquer et vérifier

Appliquez le fichier pour de bon, puis attendez que les Pods soient prêts :

```bash
kubectl apply -f ~/essai-manifeste/annuaire.yaml
kubectl rollout status deployment/annuaire -n essai-manifeste --timeout=180s | tail -1
```

```text
configmap/annuaire-config created
deployment.apps/annuaire created
service/annuaire created
deployment "annuaire" successfully rolled out
```

Les trois objets sont dans `essai-manifeste`, sans `-n` sur la commande
`apply` :

```bash
kubectl get deploy,svc,configmap -n essai-manifeste
```

```text
NAME                       READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/annuaire   2/2     2            2           8s

NAME               TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
service/annuaire   ClusterIP   10.96.205.45   <none>        80/TCP    8s

NAME                         DATA   AGE
configmap/annuaire-config    1      8s
configmap/kube-root-ca.crt   1      9s
```

Le Service trouve-t-il les deux Pods ? Ses adresses sont rangées dans des
**EndpointSlices**, qui portent le nom du Service dans un label :

```bash
kubectl get endpointslices -n essai-manifeste -l kubernetes.io/service-name=annuaire -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]}{"\n"}{end}'
```

```text
10.244.0.7
10.244.0.8
```

Deux adresses, une par Pod. Enfin, le conteneur a-t-il reçu la variable de la
ConfigMap ?

```bash
kubectl exec -n essai-manifeste deploy/annuaire -- printenv LANGUE
```

```text
fr
```

## 📚 Exercice 7 : voir l'écart avant d'appliquer

Passez le fichier à 3 réplicas, puis demandez à `kubectl diff` ce qu'un `apply`
changerait. `grep` ne garde que les lignes modifiées :

```bash
sed -i 's/^  replicas: 2/  replicas: 3/' ~/essai-manifeste/annuaire.yaml; kubectl diff -f ~/essai-manifeste/annuaire.yaml | grep -E '^[-+] '
```

```text
-  generation: 1
+  generation: 2
-  replicas: 2
+  replicas: 3
```

Le `-` montre l'état actuel, le `+` l'état après `apply`. `generation` est un
compteur que le cluster augmente à chaque modification. Appliquez :

```bash
kubectl apply -f ~/essai-manifeste/annuaire.yaml
```

```text
configmap/annuaire-config unchanged
deployment.apps/annuaire configured
service/annuaire unchanged
```

Seul le Deployment est modifié (`configured`), les deux autres objets restent
tels quels (`unchanged`).

## 📚 Exercice 8 : corriger en place un objet existant

Créez un Deployment `vitrine` fautif, avec une image qui n'existe pas :

```bash
kubectl create deployment vitrine --image=nginx:1.30.6-introuvable --replicas=1 -n essai-manifeste
sleep 20; kubectl get pods -n essai-manifeste -l app=vitrine
```

```text
deployment.apps/vitrine created
NAME                       READY   STATUS             RESTARTS   AGE
vitrine-5fcdbd9877-8t6ct   0/1     ImagePullBackOff   0          20s
```

`ImagePullBackOff` : l'image est introuvable. Notez l'**uid** du Deployment,
son identifiant unique. Un objet supprimé puis recréé en reçoit un nouveau :

```bash
kubectl get deployment vitrine -n essai-manifeste -o jsonpath='{.metadata.uid}{"\n"}'
```

```text
1639a99c-7720-49ce-88dd-6533d26237c2
```

Corrigez l'objet **en place** : `kubectl set image` change l'image du
conteneur (nommé `nginx`), et `kubectl scale` change le nombre de réplicas :

```bash
kubectl set image deployment/vitrine nginx=nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703 -n essai-manifeste; kubectl scale deployment/vitrine --replicas=2 -n essai-manifeste
kubectl rollout status deployment/vitrine -n essai-manifeste --timeout=180s | tail -1
```

```text
deployment.apps/vitrine image updated
deployment.apps/vitrine scaled
deployment "vitrine" successfully rolled out
```

Relisez l'uid et l'état :

```bash
kubectl get deployment vitrine -n essai-manifeste -o jsonpath='{.metadata.uid}{"\n"}'; kubectl get deployment vitrine -n essai-manifeste
```

```text
1639a99c-7720-49ce-88dd-6533d26237c2
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
vitrine   2/2     2            2           21s
```

Même uid : c'est le même objet, corrigé, et ses 2 Pods sont prêts. `kubectl
edit` ou un `kubectl apply` du manifeste corrigé auraient aussi gardé l'uid.
Un `kubectl delete` suivi d'un `create`, non.

## 🧹 Nettoyage

Supprimez le namespace d'essai et le répertoire de travail :

```bash
kubectl delete namespace essai-manifeste; rm -rf ~/essai-manifeste
```

```text
namespace "essai-manifeste" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-ecrire-un-manifeste
dsoxlab check k8s-ecrire-un-manifeste
```

```text
╭─ Résultat : k8s-ecrire-un-manifeste ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests     │
╰──────────────────────────────────────╯
```

0 sur 6 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : écrire le manifeste d'une autre application, dans un
autre namespace, le valider, l'appliquer, et corriger en place un Deployment
qui ne démarre pas.

```bash
dsoxlab run k8s-ecrire-un-manifeste
dsoxlab challenge k8s-ecrire-un-manifeste
```
