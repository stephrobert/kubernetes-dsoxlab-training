# Sortir un mot de passe du manifeste d'un Deployment

Une application tourne déjà, et son mot de passe est écrit **en clair** dans le
manifeste de son Deployment. Ce manifeste est versionné, relu, copié dans des
sauvegardes : tout ce qui le lit lit aussi le mot de passe. Dans ce cours, vous
mesurez ce qu'un Secret protège et ce qu'il ne protège pas, puis vous déplacez
une valeur en clair vers un Secret, sans recréer le Deployment.

Vous travaillez dans un namespace d'essai, `essai-protection`, avec une
application `facture` qui utilise un jeton d'API. Le challenge vous demandera
de protéger le mot de passe d'une autre application : vous le ferez seul, à la
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
19 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : une valeur en clair dans un Deployment

Créez le namespace d'essai et l'application `facture`, puis donnez-lui son
jeton d'API **en clair**, avec `kubectl set env`. C'est la situation que vous
allez corriger :

```bash
kubectl create namespace essai-protection
kubectl create deployment facture --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-protection -- sleep 86400
kubectl set env deployment/facture JETON_API=Orage-77 -n essai-protection
kubectl rollout status deployment/facture -n essai-protection --timeout=120s | tail -1
```

```text
namespace/essai-protection created
deployment.apps/facture created
deployment.apps/facture env updated
deployment "facture" successfully rolled out
```

`kubectl set env --list` montre les variables du Deployment :

```bash
kubectl set env deployment/facture --list -n essai-protection
kubectl get deployment facture -n essai-protection -o yaml | grep -c 'Orage-77'
```

```text
# Deployment facture, container busybox
JETON_API=Orage-77
1
```

Le jeton se lit en clair, et il apparaît une fois dans le manifeste du
Deployment.

## 📚 Exercice 2 : encodé n'est pas chiffré

Un Secret range ses valeurs encodées en base64. Encodez le jeton vous-même
(`-n` évite d'ajouter un retour à la ligne), puis décodez le résultat :

```bash
echo -n 'Orage-77' | base64
echo 'T3JhZ2UtNzc=' | base64 -d; echo
```

```text
T3JhZ2UtNzc=
Orage-77
```

N'importe qui décode une valeur en base64, sans clé ni mot de passe. Un Secret
ne rend donc pas une valeur illisible. Ce qu'il change :

- la valeur sort du manifeste de l'application, qui est copié partout ;
- l'accès au Secret se règle à part, avec des droits que l'on peut
  restreindre (exercice 5).

## 📚 Exercice 3 : stringData, sans encoder soi-même

Dans un manifeste de Secret, le champ `stringData` accepte la valeur telle
quelle : Kubernetes l'encode à votre place. La clé s'appelle ici `api` :

```bash
cat <<'YAML' | kubectl apply -n essai-protection -f -
apiVersion: v1
kind: Secret
metadata:
  name: facture-api
type: Opaque
stringData:
  api: Orage-77
YAML
kubectl get secret facture-api -n essai-protection -o jsonpath='{.data}{"\n"}'
```

```text
secret/facture-api created
{"api":"T3JhZ2UtNzc="}
```

Le Secret stocke bien la valeur encodée, dans `data`. Attention : ce manifeste,
lui, contient le jeton en clair. Ne le versionnez pas. Pour ne jamais l'écrire
dans un fichier, `kubectl create secret generic` fait le même travail en une
commande.

## 📚 Exercice 4 : brancher la variable sur le Secret

`kubectl set env --from=secret/<nom>` crée une variable par clé du Secret, qui
**fait référence** au Secret au lieu de porter la valeur. Le nom de la
variable est la clé en majuscules, précédée du préfixe donné : `JETON_` plus
`API` donne `JETON_API`, la variable qui existe déjà, et qui est remplacée.

```bash
kubectl set env deployment/facture --from=secret/facture-api --prefix=JETON_ -n essai-protection
kubectl rollout status deployment/facture -n essai-protection --timeout=120s | tail -1
```

```text
Warning: key api transferred to API
deployment.apps/facture env updated
deployment "facture" successfully rolled out
```

L'avertissement dit seulement que la clé `api` a été mise en majuscules pour
devenir un nom de variable. Relisez les variables, puis cherchez le jeton dans
le manifeste :

```bash
kubectl set env deployment/facture --list -n essai-protection
kubectl get deployment facture -n essai-protection -o yaml | grep -c 'Orage-77'
```

```text
# Deployment facture, container busybox
# JETON_API from secret facture-api, key api
0
```

`JETON_API` vient maintenant du Secret, et le jeton n'est plus dans le
manifeste. L'application, elle, le reçoit toujours :

```bash
sleep 3; kubectl exec deploy/facture -n essai-protection -- sh -c 'echo JETON_API=$JETON_API'
```

```text
JETON_API=Orage-77
```

Le Deployment a été **modifié sur place**, pas recréé : son historique garde
les trois versions.

```bash
kubectl rollout history deployment/facture -n essai-protection
```

```text
deployment.apps/facture
REVISION  CHANGE-CAUSE
1         <none>
2         <none>
3         <none>
```

La révision 1 est la création, la 2 le jeton en clair, la 3 le jeton branché
sur le Secret.

## 📚 Exercice 5 : qui peut lire le Secret

Un Secret ne protège que si l'accès est restreint. `kubectl auth can-i` répond
par `yes` ou `no` : vous, administrateur du cluster, pouvez-vous lire les
Secrets du namespace ?

```bash
kubectl auth can-i get secrets -n essai-protection
```

```text
yes
```

Et le compte de service `default`, sous lequel tournent les Pods de ce
namespace ? `--as` pose la question à sa place :

```bash
kubectl auth can-i get secrets -n essai-protection --as=system:serviceaccount:essai-protection:default
```

```text
no
```

Les Pods de l'application ne peuvent pas lire les Secrets par l'API. Ils ne
reçoivent que ce que leur manifeste leur donne, par référence.

## 📚 Exercice 6 : un Secret qu'on ne peut plus modifier

Un Secret peut être rendu **immuable** : plus personne ne peut changer ses
valeurs par erreur.

```bash
kubectl patch secret facture-api -n essai-protection -p '{"immutable":true}'
kubectl patch secret facture-api -n essai-protection -p '{"stringData":{"api":"Grele-12"}}'
kubectl get secret facture-api -n essai-protection -o jsonpath='{.data.api}' | base64 -d; echo
```

```text
secret/facture-api patched
The Secret "facture-api" is invalid: data: Forbidden: field is immutable when `immutable` is set
Orage-77
```

La modification est refusée, et la valeur n'a pas bougé. Pour changer un jeton
immuable, on crée un nouveau Secret, et on fait pointer le Deployment dessus.

## 🧹 Nettoyage

Supprimez le namespace d'essai, avec tout ce qu'il contient :

```bash
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

À vous, seul cette fois : le mot de passe d'une application est écrit en clair
dans son Deployment. Mettez-le dans un Secret, sans casser l'application.

```bash
dsoxlab run ckad-secret-injection-protection
dsoxlab challenge ckad-secret-injection-protection
```
