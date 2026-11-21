# Donner une identité à une application : ServiceAccount, Role, RoleBinding

La leçon montre un ServiceAccount, l'identité d'une application, et le jeton
qu'un Pod utilise pour parler à l'API. Ce cours se concentre sur ces jetons et
ajoute des cas que la leçon ne montre pas : faire vérifier un jeton par l'API,
un jeton qui ne vaut plus rien quand son ServiceAccount est recréé, un jeton
lié à un Pod qui meurt avec lui, et le jeton à l'ancienne, rangé dans un
Secret, qui n'expire jamais.

Vous travaillez dans un namespace d'essai, `essai-jetons`, avec un
ServiceAccount `robot`. Les jetons sont gardés dans des fichiers de votre
répertoire personnel. Le challenge porte sur un autre compte et d'autres
objets : vous le ferez seul, à la fin.

Page associée : [ServiceAccounts pour les développeurs](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/serviceaccounts-developpeurs/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-rbac-serviceaccount
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Pour vérifier un jeton, ce cours envoie à l'API un objet `TokenReview` :
l'API répond si le jeton est valide, pour quel utilisateur, ou pourquoi il est
refusé. Chaque vérification affiche `authentifié=`, `utilisateur=` et
`erreur=`.

## ✅ Exercice 1 : faire vérifier un jeton par l'API

Créez le namespace, le ServiceAccount, et un jeton valable 10 minutes avec
`kubectl create token`. La commande affiche la taille du jeton :

```bash
kubectl create namespace essai-jetons; kubectl create serviceaccount robot -n essai-jetons; kubectl create token robot -n essai-jetons --duration=10m > ~/jeton-robot; wc -c < ~/jeton-robot
```

```text
namespace/essai-jetons created
serviceaccount/robot created
938
```

Faites-le vérifier :

```bash
J=$(cat ~/jeton-robot); cat <<YAML | kubectl create -o jsonpath='authentifié={.status.authenticated} utilisateur={.status.user.username} erreur={.status.error}{"\n"}' -f -
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: $J
YAML
```

```text
authentifié=true utilisateur=system:serviceaccount:essai-jetons:robot erreur=
```

Le jeton est valide, et l'API sait à qui il appartient. Ce jeton n'est rangé
nulle part dans le cluster : l'API l'a signé, et elle sait le vérifier.

## 🔄 Exercice 2 : recréer le ServiceAccount invalide ses jetons

Supprimez puis recréez `robot`, sous le même nom, et vérifiez aussitôt le
jeton :

```bash
kubectl delete serviceaccount robot -n essai-jetons; kubectl create serviceaccount robot -n essai-jetons; J=$(cat ~/jeton-robot); cat <<YAML | kubectl create -o jsonpath='authentifié={.status.authenticated} utilisateur={.status.user.username} erreur={.status.error}{"\n"}' -f -
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: $J
YAML
```

```text
serviceaccount "robot" deleted from essai-jetons namespace
serviceaccount/robot created
authentifié=true utilisateur=system:serviceaccount:essai-jetons:robot erreur=
```

Encore valide ? L'API garde en cache, une dizaine de secondes, le résultat
d'une vérification. Le jeton avait été vérifié juste avant. Attendez 15
secondes et recommencez :

```bash
sleep 15; J=$(cat ~/jeton-robot); cat <<YAML | kubectl create -o jsonpath='authentifié={.status.authenticated} utilisateur={.status.user.username} erreur={.status.error}{"\n"}' -f -
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: $J
YAML
```

```text
authentifié= utilisateur= erreur=[invalid bearer token, service account UID (adb05be1-d9f4-4d91-8e35-f8bf3651446d) does not match claim (f8ea8498-dc9f-4726-b7f5-f144aa424186)]
```

Refusé : le jeton porte l'UID de l'ancien `robot`, et le nouveau en a un
autre. Un jeton est attaché à un objet précis, pas à un nom. Recréer un
ServiceAccount coupe donc tous ses jetons, après au plus quelques secondes.

## 🔗 Exercice 3 : un jeton qui meurt avec son Pod

Créez un Pod qui utilise `robot`, puis un jeton lié à ce Pod
(`--bound-object-kind` et `--bound-object-name`), et vérifiez-le. Le Pod doit
utiliser le même ServiceAccount, sinon l'API refuse de lier le jeton :

```bash
kubectl run porteur --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-jetons --overrides='{"spec":{"serviceAccountName":"robot"}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/porteur -n essai-jetons --timeout=120s; kubectl create token robot -n essai-jetons --bound-object-kind=Pod --bound-object-name=porteur > ~/jeton-lie; J=$(cat ~/jeton-lie); cat <<YAML | kubectl create -o jsonpath='authentifié={.status.authenticated} utilisateur={.status.user.username} erreur={.status.error}{"\n"}' -f -
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: $J
YAML
```

```text
pod/porteur created
pod/porteur condition met
authentifié=true utilisateur=system:serviceaccount:essai-jetons:robot erreur=
```

Supprimez le Pod, attendez 15 secondes, et revérifiez :

```bash
kubectl delete pod porteur -n essai-jetons; sleep 15; J=$(cat ~/jeton-lie); cat <<YAML | kubectl create -o jsonpath='authentifié={.status.authenticated} utilisateur={.status.user.username} erreur={.status.error}{"\n"}' -f -
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: $J
YAML
```

```text
pod "porteur" deleted from essai-jetons namespace
authentifié= utilisateur= erreur=[invalid bearer token, service account token has been invalidated]
```

Le jeton est mort avec le Pod. C'est le cas de ceux que le kubelet monte dans
les Pods : un jeton volé dans un Pod supprimé ne sert plus à rien.

## 🗝️ Exercice 4 : le jeton à l'ancienne, qui n'expire pas

Avant Kubernetes 1.24, chaque ServiceAccount recevait un jeton rangé dans un
Secret. On peut encore en créer un, avec un Secret de type
`kubernetes.io/service-account-token`. Créez-le, extrayez le jeton, puis
lisez trois champs de son contenu : la date d'expiration (`exp`), la date
d'émission (`iat`) et le titulaire (`sub`) :

```bash
cat <<'YAML' | kubectl apply -n essai-jetons -f -
apiVersion: v1
kind: Secret
metadata:
  name: ancien-jeton
  annotations:
    kubernetes.io/service-account.name: robot
type: kubernetes.io/service-account-token
YAML
sleep 3; kubectl get secret ancien-jeton -n essai-jetons -o jsonpath='{.data.token}' | base64 -d > ~/jeton-ancien; cut -d. -f2 ~/jeton-ancien | tr '_-' '/+' | base64 -d 2>/dev/null | tr ',' '\n' | grep -E '"(exp|iat|sub)"'; echo
```

```text
secret/ancien-jeton created
"sub":"system:serviceaccount:essai-jetons:robot"}
```

Seul `sub` existe : ce jeton n'a ni date d'émission ni date d'expiration. Il
est valide tant que son Secret existe :

```bash
J=$(cat ~/jeton-ancien); cat <<YAML | kubectl create -o jsonpath='authentifié={.status.authenticated} utilisateur={.status.user.username} erreur={.status.error}{"\n"}' -f -
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: $J
YAML
```

```text
authentifié=true utilisateur=system:serviceaccount:essai-jetons:robot erreur=
```

Supprimez le Secret et vérifiez aussitôt, puis 15 secondes plus tard :

```bash
kubectl delete secret ancien-jeton -n essai-jetons; J=$(cat ~/jeton-ancien); cat <<YAML | kubectl create -o jsonpath='authentifié={.status.authenticated} utilisateur={.status.user.username} erreur={.status.error}{"\n"}' -f -
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: $J
YAML
```

```text
secret "ancien-jeton" deleted from essai-jetons namespace
authentifié=true utilisateur=system:serviceaccount:essai-jetons:robot erreur=
```

```bash
sleep 15; J=$(cat ~/jeton-ancien); cat <<YAML | kubectl create -o jsonpath='authentifié={.status.authenticated} utilisateur={.status.user.username} erreur={.status.error}{"\n"}' -f -
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: $J
YAML
```

```text
authentifié= utilisateur= erreur=[invalid bearer token, Token has been invalidated]
```

D'abord encore accepté à cause du cache, puis refusé. Un tel jeton, s'il
fuit, reste utilisable jusqu'à ce que quelqu'un pense à supprimer son Secret.
Préférez les jetons à durée limitée de `kubectl create token`.

## 🧹 Nettoyage

Supprimez le namespace d'essai et les fichiers des jetons :

```bash
kubectl delete namespace essai-jetons; rm -f ~/jeton-robot ~/jeton-lie ~/jeton-ancien
```

```text
namespace "essai-jetons" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-rbac-serviceaccount
dsoxlab check cka-rbac-serviceaccount
```

```text
╭─ Résultat : cka-rbac-serviceaccount ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests     │
╰──────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une application qui doit lire les Pods de son
namespace avec sa propre identité, et une autre qui ne doit porter aucun
jeton.

```bash
dsoxlab run cka-rbac-serviceaccount
dsoxlab challenge cka-rbac-serviceaccount
```
