# Sortir un mot de passe du manifeste d'un Deployment

Une application tourne déjà, et son jeton d'API est écrit **en clair** dans le
manifeste de son Deployment. Ce manifeste est versionné, relu, copié dans des
sauvegardes : tout ce qui le lit lit aussi le jeton. La leçon déplace une
telle valeur vers un Secret en réappliquant le manifeste. Ce cours prend un
autre chemin, `kubectl set env`, et regarde où le jeton reste quand même :
dans une annotation du Deployment et dans son historique. Il se termine par le
geste qui règle le problème pour de bon : changer le jeton.

Vous travaillez dans un namespace d'essai, `essai-protection`, avec une
application `facture` qui utilise un jeton d'API. Le challenge vous demandera
de traiter le mot de passe d'une autre application : vous le ferez seul, à la
fin.

Page associée : [Secrets Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/secrets/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-secret-injection-protection
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : un jeton en clair, posé par kubectl apply

Créez le namespace d'essai, puis le Deployment `facture` avec `kubectl apply`,
comme on le fait d'ordinaire depuis un fichier versionné. Son jeton d'API,
`JETON_API`, est écrit en clair :

```bash
kubectl create namespace essai-protection
cat > ~/facture.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: facture
spec:
  replicas: 1
  selector:
    matchLabels:
      app: facture
  template:
    metadata:
      labels:
        app: facture
    spec:
      terminationGracePeriodSeconds: 2
      containers:
        - name: facture
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sleep", "86400"]
          env:
            - name: JETON_API
              value: Orage-77
YAML
kubectl apply -n essai-protection -f ~/facture.yaml
kubectl rollout status deployment/facture -n essai-protection --timeout=120s | tail -1
```

```text
namespace/essai-protection created
deployment.apps/facture created
deployment "facture" successfully rolled out
```

Comptez les lignes du manifeste qui contiennent le jeton, puis affichez-les.
`grep -n` donne leur numéro, et `cut` coupe les lignes trop longues :

```bash
kubectl get deployment facture -n essai-protection -o yaml | grep -c 'Orage-77'
kubectl get deployment facture -n essai-protection -o yaml | grep -n 'Orage-77' | cut -c1-120
```

```text
2
7:      {"apiVersion":"apps/v1","kind":"Deployment","metadata":{"annotations":{},"name":"facture","namespace":"essai-pro
37:          value: Orage-77
```

Deux lignes. La ligne 37 est le champ `env`. La ligne 7 est l'annotation
`kubectl.kubernetes.io/last-applied-configuration` : `kubectl apply` y garde
une copie complète du manifeste appliqué, jeton compris.

## 📚 Exercice 2 : un Secret écrit avec stringData

Dans un manifeste de Secret, le champ `stringData` accepte la valeur telle
quelle : Kubernetes l'encode à votre place. La clé s'appelle ici `api` :

```bash
cat > ~/facture-api.yaml <<'YAML'
apiVersion: v1
kind: Secret
metadata:
  name: facture-api
type: Opaque
stringData:
  api: Orage-77
YAML
kubectl apply -n essai-protection -f ~/facture-api.yaml
kubectl get secret facture-api -n essai-protection -o jsonpath='{.data}{"\n"}'
```

```text
secret/facture-api created
{"api":"T3JhZ2UtNzc="}
```

Le Secret stocke la valeur encodée en base64, dans `data`. Le fichier
`~/facture-api.yaml`, lui, contient le jeton en clair : ne le versionnez pas.

## 📚 Exercice 3 : set env, puis l'annotation qui reste

`kubectl set env --from=secret/<nom>` crée une variable par clé du Secret, qui
**fait référence** au Secret au lieu de porter la valeur. Le nom de la
variable est la clé en majuscules, précédée du préfixe donné : `JETON_` plus
`API` donne `JETON_API`, la variable qui existe déjà, et qui est remplacée.

```bash
kubectl set env deployment/facture --from=secret/facture-api --prefix=JETON_ -n essai-protection
kubectl rollout status deployment/facture -n essai-protection --timeout=120s | tail -1
kubectl set env deployment/facture --list -n essai-protection
```

```text
Warning: key api transferred to API
deployment.apps/facture env updated
deployment "facture" successfully rolled out
# Deployment facture, container facture
# JETON_API from secret facture-api, key api
```

L'avertissement dit seulement que la clé `api` a été mise en majuscules pour
devenir un nom de variable. `JETON_API` vient maintenant du Secret. Cherchez
de nouveau le jeton dans le manifeste :

```bash
kubectl get deployment facture -n essai-protection -o yaml | grep -c 'Orage-77'
kubectl get deployment facture -n essai-protection -o yaml | grep -n 'Orage-77' | cut -c1-120
```

```text
1
7:      {"apiVersion":"apps/v1","kind":"Deployment","metadata":{"annotations":{},"name":"facture","namespace":"essai-pro
```

Le champ `env` est propre, mais l'annotation garde le jeton : `kubectl set
env` ne la met pas à jour (`kubectl edit` non plus). Seul `kubectl apply` la
réécrit. Deux façons de s'en défaire : réappliquer le manifeste corrigé en
entier, comme dans la leçon, ou retirer l'annotation. Ici, retirez-la : le `-`
final de `kubectl annotate` supprime une annotation.

```bash
kubectl annotate deployment facture kubectl.kubernetes.io/last-applied-configuration- -n essai-protection
kubectl get deployment facture -n essai-protection -o yaml | grep -c 'Orage-77'
```

```text
deployment.apps/facture annotated
0
```

Le manifeste ne contient plus le jeton. L'application, elle, le reçoit
toujours :

```bash
sleep 3; kubectl exec deploy/facture -n essai-protection -- sh -c 'echo JETON_API=$JETON_API'
```

```text
JETON_API=Orage-77
```

## 📚 Exercice 4 : l'historique garde le jeton

Le Deployment a été modifié sur place. Son historique compte deux révisions :

```bash
kubectl rollout history deployment/facture -n essai-protection
```

```text
deployment.apps/facture
REVISION  CHANGE-CAUSE
1         <none>
2         <none>
```

Chaque révision est un ReplicaSet, gardé pour permettre un retour arrière.
Lisez la révision 1 :

```bash
kubectl rollout history deployment/facture -n essai-protection --revision=1 | grep -A1 JETON
kubectl get replicasets -n essai-protection
kubectl get replicasets -n essai-protection -o yaml | grep -c 'Orage-77'
```

```text
      JETON_API:	Orage-77
    Mounts:	<none>
NAME                 DESIRED   CURRENT   READY   AGE
facture-6d5f5b5987   0         0         0       5s
facture-f5945d56f    1         1         1       4s
```

```text title="Fin de la sortie"
1
```

L'ancien ReplicaSet, à 0 Pod, porte toujours le jeton en clair. Le
Deployment en garde dix par défaut. Le jeton a donc circulé en clair, et il se
lit encore : la seule correction sûre est de le **changer**. L'exercice 6 le
fait.

## 📚 Exercice 5 : qui peut lire le Secret

Un Secret ne protège que si l'accès est restreint. `kubectl auth can-i` répond
par `yes` ou `no`. Vous, administrateur du cluster, pouvez-vous lire les
Secrets du namespace ?

```bash
kubectl auth can-i get secrets -n essai-protection
```

```text
yes
```

Les Pods de ce namespace tournent sous un compte de service, `default`, dont le
nom complet est `system:serviceaccount:essai-protection:default`. `--as` pose
la question à sa place :

```bash
kubectl auth can-i get secrets -n essai-protection --as=system:serviceaccount:essai-protection:default
kubectl auth can-i create pods -n essai-protection --as=system:serviceaccount:essai-protection:default
```

```text
no
no
```

Ce compte ne peut ni lire les Secrets par l'API, ni créer de Pods. Le second
point compte autant que le premier : la documentation de Kubernetes rappelle
que quiconque peut créer un Pod dans un namespace peut y monter n'importe quel
Secret de ce namespace, et donc le lire. Restreindre l'accès aux Secrets, c'est
aussi restreindre qui crée des Pods.

## 📚 Exercice 6 : changer le jeton par un Secret immuable

Créez le nouveau jeton dans un nouveau Secret, `facture-api-v2`, marqué
`immutable: true` : plus personne ne pourra changer sa valeur par erreur.

```bash
cat > ~/facture-api-v2.yaml <<'YAML'
apiVersion: v1
kind: Secret
metadata:
  name: facture-api-v2
type: Opaque
immutable: true
stringData:
  api: Grele-12
YAML
kubectl apply -n essai-protection -f ~/facture-api-v2.yaml
kubectl patch secret facture-api-v2 -n essai-protection -p '{"stringData":{"api":"Neige-3"}}'
```

```text
secret/facture-api-v2 created
The Secret "facture-api-v2" is invalid: data: Forbidden: field is immutable when `immutable` is set
```

La modification est refusée. Faites pointer le Deployment sur le nouveau
Secret, vérifiez ce que voit l'application, puis supprimez l'ancien Secret :

```bash
kubectl set env deployment/facture --from=secret/facture-api-v2 --prefix=JETON_ -n essai-protection
kubectl rollout status deployment/facture -n essai-protection --timeout=120s | tail -1
kubectl set env deployment/facture --list -n essai-protection
sleep 3; kubectl exec deploy/facture -n essai-protection -- sh -c 'echo JETON_API=$JETON_API'
kubectl delete secret facture-api -n essai-protection
```

```text
Warning: key api transferred to API
deployment.apps/facture env updated
deployment "facture" successfully rolled out
# Deployment facture, container facture
# JETON_API from secret facture-api-v2, key api
JETON_API=Grele-12
secret "facture-api" deleted from essai-protection namespace
```

L'application utilise le nouveau jeton. L'ancien, `Orage-77`, reste lisible
dans la révision 1, mais il ne vaut plus rien une fois révoqué chez le service
qui l'avait émis. C'est ce qu'on attend d'un changement de jeton.

## 🧹 Nettoyage

Supprimez les fichiers de travail et le namespace d'essai :

```bash
rm -f ~/facture.yaml ~/facture-api.yaml ~/facture-api-v2.yaml
kubectl delete namespace essai-protection
```

```text
namespace "essai-protection" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-secret-injection-protection
dsoxlab check ckad-secret-injection-protection
```

```text
╭─ Résultat : ckad-secret-injection-protection ─╮
│  0 / 100 pts                                  │
│  ░░░░░░░░░░░░░░░░░░░░  0/9 tests              │
╰───────────────────────────────────────────────╯
```

0 sur 9 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : le mot de passe d'une application a fuité, et il est
écrit en clair dans son Deployment. Rangez le nouveau dans un Secret, et
faites disparaître l'ancien du manifeste.

```bash
dsoxlab run ckad-secret-injection-protection
dsoxlab challenge ckad-secret-injection-protection
```
