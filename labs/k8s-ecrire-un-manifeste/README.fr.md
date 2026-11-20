# Écrire et valider un manifeste

Un **manifeste** est un fichier YAML qui décrit des objets Kubernetes. On le
garde dans un dépôt Git, et on le rejoue autant de fois que nécessaire. La
leçon montre comment l'écrire, le valider et l'appliquer. Ce cours s'arrête
sur ce qui tourne mal ensuite : un Service qui ne trouve aucun Pod, un objet
qui atterrit dans le mauvais namespace, un fichier qui n'est appliqué qu'à
moitié, une valeur que seul le serveur refuse, un cluster qui ne dit plus la
même chose que le fichier, et un objet à corriger sans le recréer.

Vous travaillez dans un namespace d'essai, `essai-manifeste`, avec une
application `annuaire`. Le challenge vous demandera de réparer le manifeste
d'une autre application : vous le ferez seul, à la fin.

Page associée : [Écrire des Manifests](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/ecrire-manifests/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-ecrire-un-manifeste
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`lab` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026, avec Kubernetes 1.37.

## 📚 Exercice 1 : un Service qui ne trouve aucun Pod

Créez le namespace d'essai, puis le manifeste de l'application : une
ConfigMap, un Deployment et un Service, séparés par des lignes `---`. Chaque
objet nomme son namespace. Le sélecteur du Service contient une faute de
frappe, `anuaire` :

```bash
kubectl create namespace essai-manifeste; mkdir -p ~/essai-manifeste
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
    app: anuaire
  ports:
    - port: 80
      targetPort: 80
YAML
```

```text
namespace/essai-manifeste created
```

Faites valider le fichier par le serveur, puis appliquez-le :

```bash
kubectl apply -f ~/essai-manifeste/annuaire.yaml --dry-run=server
kubectl apply -f ~/essai-manifeste/annuaire.yaml; kubectl rollout status deployment/annuaire -n essai-manifeste --timeout=180s | tail -1
```

```text
configmap/annuaire-config created (server dry run)
deployment.apps/annuaire created (server dry run)
service/annuaire created (server dry run)
configmap/annuaire-config created
deployment.apps/annuaire created
service/annuaire created
deployment "annuaire" successfully rolled out
```

Le serveur accepte tout, et les Pods tournent. Le Service trouve-t-il les
Pods ? Ses adresses sont rangées dans des **EndpointSlices**, qui portent le
nom du Service dans un label :

```bash
kubectl get endpointslices -n essai-manifeste -l kubernetes.io/service-name=annuaire
```

```text
NAME             ADDRESSTYPE   PORTS     ENDPOINTS   AGE
annuaire-mwmhx   IPv4          <unset>   <unset>     11s
```

`<unset>` : aucune adresse. Le serveur ne vérifie pas qu'un sélecteur trouve
quelque chose, un Service vide est un objet valide. Comparez le sélecteur du
Service aux labels des Pods :

```bash
kubectl get service annuaire -n essai-manifeste -o jsonpath='{.spec.selector}{"\n"}'; kubectl get pods -n essai-manifeste --show-labels
```

```text
{"app":"anuaire"}
NAME                        READY   STATUS    RESTARTS   AGE   LABELS
annuaire-76c8d45764-jpl5l   1/1     Running   0          11s   app=annuaire,pod-template-hash=76c8d45764
annuaire-76c8d45764-m777c   1/1     Running   0          11s   app=annuaire,pod-template-hash=76c8d45764
```

Le Service cherche `app=anuaire`, les Pods portent `app=annuaire`. Corrigez le
fichier, puis appliquez-le de nouveau :

```bash
sed -i 's/app: anuaire/app: annuaire/' ~/essai-manifeste/annuaire.yaml; kubectl apply -f ~/essai-manifeste/annuaire.yaml
sleep 3; kubectl get endpointslices -n essai-manifeste -l kubernetes.io/service-name=annuaire
```

```text
configmap/annuaire-config unchanged
deployment.apps/annuaire unchanged
service/annuaire configured
NAME             ADDRESSTYPE   PORTS   ENDPOINTS                 AGE
annuaire-mwmhx   IPv4          80      10.244.0.65,10.244.0.66   15s
```

Seul le Service change (`configured`), et il trouve maintenant les deux Pods.
Le conteneur a bien reçu la variable de la ConfigMap :

```bash
kubectl exec -n essai-manifeste deploy/annuaire -- printenv LANGUE
```

```text
fr
```

## 📚 Exercice 2 : sans namespace, l'objet va dans le contexte courant

Regardez le namespace de votre contexte courant (`echo '(fin)'` marque la fin
de la sortie) :

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
où pointe le contexte de celui qui l'applique. Supprimez-le :

```bash
kubectl delete configmap essai-perdu
```

```text
configmap "essai-perdu" deleted from default namespace
```

## 📚 Exercice 3 : un fichier appliqué à moitié

Écrivez un fichier de trois ConfigMaps. Dans la deuxième, `tarifs`, la ligne
`reduit` a un espace de trop au début :

```bash
cat > ~/essai-manifeste/horaires.yaml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: horaires
  namespace: essai-manifeste
data:
  ouverture: "8h"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: tarifs
  namespace: essai-manifeste
data:
  ticket: "2 euros"
   reduit: "1 euro"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: contacts
  namespace: essai-manifeste
data:
  accueil: "poste 12"
YAML
kubectl apply -f ~/essai-manifeste/horaires.yaml
```

```text
configmap/horaires created
error: error parsing /home/ansible/essai-manifeste/horaires.yaml: error converting YAML to JSON: yaml: line 7: did not find expected key
```

Une création, puis une erreur. Regardez ce qui existe vraiment :

```bash
kubectl get configmaps -n essai-manifeste
```

```text
NAME               DATA   AGE
annuaire-config    1      15s
horaires           1      0s
kube-root-ca.crt   1      16s
```

`horaires` existe, mais ni `tarifs`, le document fautif, ni `contacts`, qui
était pourtant juste. kubectl lit le fichier document par document, applique
chacun dès qu'il est lu, et s'arrête au premier qu'il ne sait pas lire. Le
cluster reste dans un état intermédiaire : relisez toujours ce qui a été créé
après une erreur.

Le message dit `line 7`, alors que la faute est plus bas dans le fichier : le
numéro compte depuis le début du document fautif. La ligne 7 du deuxième
document est la ligne 15 du fichier. `cat -A` marque la fin de chaque ligne
par un `$`, ce qui rend les espaces visibles :

```bash
sed -n '15,16p' ~/essai-manifeste/horaires.yaml | cat -A
```

```text
  ticket: "2 euros"$
   reduit: "1 euro"$
```

`reduit` a trois espaces au lieu de deux. Une erreur de syntaxe YAML se voit
aussi sans le serveur : `--dry-run=client` l'aurait signalée avant toute
création.

## 📚 Exercice 4 : valider côté client, puis côté serveur

Une faute de **valeur**, elle, ne se voit pas toujours sans le serveur.
Fabriquez une copie fautive du manifeste : `sed` ajoute au conteneur un
`imagePullPolicy` dont la valeur n'existe pas (`Parfois`) :

```bash
sed 's/^          ports:/          imagePullPolicy: Parfois\n          ports:/' ~/essai-manifeste/annuaire.yaml > ~/essai-manifeste/faux.yaml; grep -n imagePullPolicy ~/essai-manifeste/faux.yaml
```

```text
27:          imagePullPolicy: Parfois
```

Faites-la valider par kubectl seul, puis par le serveur, sans rien créer :

```bash
kubectl apply -f ~/essai-manifeste/faux.yaml --dry-run=client
kubectl apply -f ~/essai-manifeste/faux.yaml --dry-run=server
```

```text
configmap/annuaire-config unchanged (dry run)
deployment.apps/annuaire configured (dry run)
service/annuaire unchanged (dry run)
configmap/annuaire-config unchanged (server dry run)
service/annuaire unchanged (server dry run)
The Deployment "annuaire" is invalid: spec.template.spec.containers[0].imagePullPolicy: Unsupported value: "Parfois": supported values: "Always", "IfNotPresent", "Never"
```

kubectl seul ne voit rien. Le serveur refuse le Deployment, nomme le champ
fautif et donne les valeurs acceptées. Seul `--dry-run=server` passe le
fichier aux mêmes contrôles qu'un vrai `apply`.

## 📚 Exercice 5 : le cluster ne dit plus ce que dit le fichier

Quelqu'un passe le Deployment à 4 réplicas à la main, sans toucher au
fichier :

```bash
kubectl scale deployment/annuaire --replicas=4 -n essai-manifeste; kubectl rollout status deployment/annuaire -n essai-manifeste --timeout=120s | tail -1
grep -n 'replicas:' ~/essai-manifeste/annuaire.yaml
```

```text
deployment.apps/annuaire scaled
deployment "annuaire" successfully rolled out
15:  replicas: 2
```

Le cluster dit 4, le fichier dit toujours 2. Avant d'appliquer le fichier,
demandez à `kubectl diff` ce qu'un `apply` changerait. `grep` ne garde que les
lignes modifiées :

```bash
kubectl diff -f ~/essai-manifeste/annuaire.yaml | grep -E '^[-+] '
```

```text
-  generation: 2
+  generation: 3
-  replicas: 4
+  replicas: 2
```

Le `-` montre l'état actuel, le `+` l'état après `apply` : appliquer le
fichier ramènerait le Deployment à 2 réplicas. `generation` est un compteur
que le cluster augmente à chaque modification. Ici, c'est voulu : le fichier
fait foi. Appliquez :

```bash
kubectl apply -f ~/essai-manifeste/annuaire.yaml; sleep 5; kubectl get deployment annuaire -n essai-manifeste
```

```text
configmap/annuaire-config unchanged
deployment.apps/annuaire configured
service/annuaire unchanged
NAME       READY   UP-TO-DATE   AVAILABLE   AGE
annuaire   2/2     2            2           22s
```

Si la modification à la main était voulue, c'est le fichier qu'il fallait
corriger. `kubectl diff` sert à le voir avant d'écraser le travail d'un
collègue.

## 📚 Exercice 6 : corriger en place un objet existant

Créez un Deployment `vitrine` fautif, avec une image qui n'existe pas :

```bash
kubectl create deployment vitrine --image=nginx:1.30.6-introuvable --replicas=1 -n essai-manifeste
sleep 20; kubectl get pods -n essai-manifeste -l app=vitrine
```

```text
deployment.apps/vitrine created
NAME                       READY   STATUS             RESTARTS   AGE
vitrine-5fcdbd9877-mfxvh   0/1     ImagePullBackOff   0          20s
```

`ImagePullBackOff` : l'image est introuvable. Notez l'**uid** du Deployment,
son identifiant unique. Un objet supprimé puis recréé en reçoit un nouveau :

```bash
kubectl get deployment vitrine -n essai-manifeste -o jsonpath='{.metadata.uid}{"\n"}'
```

```text
ff84739a-7956-42b9-b6c0-81c17466cad1
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
ff84739a-7956-42b9-b6c0-81c17466cad1
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
vitrine   2/2     2            2           21s
```

Même uid : c'est le même objet, corrigé, et ses 2 Pods sont prêts. `kubectl
edit` ou un `kubectl apply` du manifeste corrigé auraient aussi gardé l'uid.
Un `kubectl delete` suivi d'un `create`, non.

## 🧹 Nettoyage

Supprimez les fichiers de travail et le namespace d'essai :

```bash
rm -rf ~/essai-manifeste; kubectl delete namespace essai-manifeste
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

À vous, seul cette fois : le manifeste d'une autre application est faux.
Réparez-le, faites-le valider par le serveur, puis appliquez-le pour mettre à
jour en place l'ancienne version qui tourne.

```bash
dsoxlab run k8s-ecrire-un-manifeste
dsoxlab challenge k8s-ecrire-un-manifeste
```
