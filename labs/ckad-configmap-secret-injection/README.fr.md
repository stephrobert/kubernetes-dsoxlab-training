# Donner des identifiants à une application avec un Secret

Un mot de passe ne doit pas être écrit dans le manifeste d'un Pod : ce
manifeste est versionné, relu, copié. Kubernetes range les valeurs sensibles
dans un objet à part, le **Secret**. Le Pod n'y fait qu'une **référence**, et
la valeur n'apparaît qu'à l'intérieur du conteneur, en variable
d'environnement ou en fichier. La leçon montre comment créer, lire et injecter
un Secret. Ce cours donne des Secrets à une application de trois façons, puis
regarde deux situations que la leçon décrit sans les montrer : une même clé
fournie par deux sources, et un Secret modifié alors que le Pod tourne.

Vous travaillez dans un namespace d'essai, `essai-secret`, avec une application
`courrier` qui a besoin d'identifiants pour envoyer des e-mails. Le challenge
vous demandera de configurer une autre application : vous le ferez seul, à la
fin.

Page associée : [Secrets Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/secrets/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-configmap-secret-injection
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : deux Secrets

Créez le namespace d'essai et deux Secrets. Le type `generic` est le Secret
ordinaire :

- `smtp-identifiants` porte deux valeurs, `SMTP_USER` et `SMTP_PASSWORD` ;
- `smtp-relais` porte un fichier entier, `relais.conf`, dont le nom devient la
  clé.

```bash
kubectl create namespace essai-secret
kubectl create secret generic smtp-identifiants --from-literal=SMTP_USER=courrier --from-literal=SMTP_PASSWORD='Pluie-2026' -n essai-secret
printf 'serveur=smtp.exemple.fr\nport=587\n' > ~/relais.conf
kubectl create secret generic smtp-relais --from-file=$HOME/relais.conf -n essai-secret
kubectl get secrets -n essai-secret
```

```text
namespace/essai-secret created
secret/smtp-identifiants created
secret/smtp-relais created
NAME                TYPE     DATA   AGE
smtp-identifiants   Opaque   2      0s
smtp-relais         Opaque   1      0s
```

`Opaque` est le nom technique du type `generic`, et la colonne `DATA` compte
les clés. `describe` les liste sans montrer leur valeur, seulement leur
taille :

```bash
kubectl describe secret smtp-identifiants -n essai-secret | sed -n '/^Data/,$p'
```

```text
Data
====
SMTP_PASSWORD:  10 bytes
SMTP_USER:      8 bytes
```

## 📚 Exercice 2 : injecter une clé, toutes les clés, ou un fichier

Le Pod `courrier` reçoit les Secrets de trois façons :

- `env` avec `secretKeyRef` : **une** clé, `SMTP_PASSWORD`, sous le nom de
  variable de votre choix, ici `MOT_DE_PASSE` ;
- `envFrom` avec `secretRef` : **toutes** les clés du Secret, chacune sous son
  propre nom ;
- un volume `secret`, monté sur `/etc/relais` : chaque clé de `smtp-relais` y
  devient un fichier, lisible par son seul propriétaire (`defaultMode: 0400`).

Écrivez le manifeste dans un fichier, puis appliquez-le :

```bash
cat > ~/courrier.yaml <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: courrier
spec:
  terminationGracePeriodSeconds: 2
  containers:
    - name: courrier
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "86400"]
      env:
        - name: MOT_DE_PASSE
          valueFrom:
            secretKeyRef:
              name: smtp-identifiants
              key: SMTP_PASSWORD
      envFrom:
        - secretRef:
            name: smtp-identifiants
      volumeMounts:
        - name: relais
          mountPath: /etc/relais
          readOnly: true
  volumes:
    - name: relais
      secret:
        secretName: smtp-relais
        defaultMode: 0400
YAML
kubectl apply -n essai-secret -f ~/courrier.yaml
kubectl wait --for=condition=Ready pod/courrier -n essai-secret --timeout=90s
kubectl exec courrier -n essai-secret -- sh -c 'echo MOT_DE_PASSE=$MOT_DE_PASSE; echo SMTP_USER=$SMTP_USER SMTP_PASSWORD=$SMTP_PASSWORD'
```

```text
pod/courrier created
pod/courrier condition met
MOT_DE_PASSE=Pluie-2026
SMTP_USER=courrier SMTP_PASSWORD=Pluie-2026
```

`MOT_DE_PASSE` vient de la référence clé par clé. `SMTP_USER` et
`SMTP_PASSWORD` viennent de `envFrom`, qui a repris les noms des clés.
Regardez maintenant le dossier monté (`-L` montre le vrai fichier, pas le lien
que Kubernetes pose devant) :

```bash
kubectl exec courrier -n essai-secret -- ls -lL /etc/relais
kubectl exec courrier -n essai-secret -- cat /etc/relais/relais.conf
```

```text
total 4
-r--------    1 root     root            33 Nov 20 12:19 relais.conf
serveur=smtp.exemple.fr
port=587
```

Le fichier `relais.conf` est là, en clair, avec les droits `-r--------` :
lisible par son seul propriétaire, comme demandé par `defaultMode: 0400`.

Le but d'un Secret est de garder la valeur hors du manifeste. Cherchez le mot
de passe dans tout le manifeste du Pod :

```bash
kubectl get pod courrier -n essai-secret -o yaml | grep -c 'Pluie-2026'
```

```text
0
```

Zéro occurrence : le Pod ne porte que des références.

## 📚 Exercice 3 : une même clé dans deux sources

Un Pod reçoit souvent un ConfigMap et un Secret par `envFrom`. Si les deux ont
une clé de même nom, une seule valeur arrive dans le conteneur. Créez un
ConfigMap `courrier-reglages` dont la clé `SMTP_USER` existe aussi dans
`smtp-identifiants`, avec une autre valeur :

```bash
kubectl create configmap courrier-reglages --from-literal=SMTP_USER=robot --from-literal=SMTP_PORT=587 --from-literal=PORT_SECOURS=2525 -n essai-secret
```

```text
configmap/courrier-reglages created
```

Le Pod `doublon` reçoit le Secret puis le ConfigMap par `envFrom`, dans cet
ordre. Il déclare aussi, dans `env`, une variable `SMTP_PORT` remplie par la
clé `PORT_SECOURS` : `SMTP_PORT` arrive donc deux fois, par `envFrom` et par
`env`.

```bash
cat > ~/doublon.yaml <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: doublon
spec:
  terminationGracePeriodSeconds: 2
  containers:
    - name: doublon
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "86400"]
      envFrom:
        - secretRef:
            name: smtp-identifiants
        - configMapRef:
            name: courrier-reglages
      env:
        - name: SMTP_PORT
          valueFrom:
            configMapKeyRef:
              name: courrier-reglages
              key: PORT_SECOURS
YAML
kubectl apply -n essai-secret -f ~/doublon.yaml
kubectl wait --for=condition=Ready pod/doublon -n essai-secret --timeout=90s
kubectl exec doublon -n essai-secret -- sh -c 'echo SMTP_USER=$SMTP_USER SMTP_PASSWORD=$SMTP_PASSWORD SMTP_PORT=$SMTP_PORT'
```

```text
pod/doublon created
pod/doublon condition met
SMTP_USER=robot SMTP_PASSWORD=Pluie-2026 SMTP_PORT=2525
```

Deux résultats :

- `SMTP_USER` vaut `robot`, la valeur du ConfigMap. Dans `envFrom`, c'est la
  **dernière** source de la liste qui l'emporte ;
- `SMTP_PORT` vaut `2525`, la valeur venue de `env`, et non `587`. Une
  variable de `env` l'emporte toujours sur `envFrom`.

Vérifiez la première règle en inversant l'ordre. Les variables d'un Pod ne se
modifient pas : supprimez le Pod, échangez les deux entrées de `envFrom` dans
le fichier, puis recréez-le. La commande `sed` fait l'échange, et la seconde
affiche le résultat :

```bash
kubectl delete pod doublon -n essai-secret
sed -i '/secretRef:/{N;h;d};/configMapRef:/{N;G}' ~/doublon.yaml
sed -n '/envFrom/,/env:/p' ~/doublon.yaml
kubectl apply -n essai-secret -f ~/doublon.yaml
kubectl wait --for=condition=Ready pod/doublon -n essai-secret --timeout=90s
kubectl exec doublon -n essai-secret -- sh -c 'echo SMTP_USER=$SMTP_USER SMTP_PASSWORD=$SMTP_PASSWORD SMTP_PORT=$SMTP_PORT'
```

```text
pod "doublon" deleted from essai-secret namespace
      envFrom:
        - configMapRef:
            name: courrier-reglages
        - secretRef:
            name: smtp-identifiants
      env:
pod/doublon created
pod/doublon condition met
SMTP_USER=courrier SMTP_PASSWORD=Pluie-2026 SMTP_PORT=2525
```

Le Secret est maintenant le dernier : `SMTP_USER` vaut `courrier`.
`SMTP_PORT` vaut toujours `2525`, puisque `env` passe avant `envFrom`. Aucune
erreur ni aucun avertissement ne signale ces doublons : un ConfigMap placé
après un Secret peut remplacer un identifiant sans que rien ne le dise.

## 📚 Exercice 4 : un Secret modifié pendant que le Pod tourne

Changez le mot de passe dans `smtp-identifiants`, puis le port dans le fichier
de `smtp-relais`. `stringData` accepte une valeur en clair, que Kubernetes
encode lui-même :

```bash
kubectl patch secret smtp-identifiants -n essai-secret -p '{"stringData":{"SMTP_PASSWORD":"Neige-2027"}}'
printf 'serveur=smtp.exemple.fr\nport=465\n' > ~/relais.conf
kubectl create secret generic smtp-relais --from-file=$HOME/relais.conf -n essai-secret --dry-run=client -o yaml | kubectl replace -f -
```

```text
secret/smtp-identifiants patched
secret/smtp-relais replaced
```

Mesurez combien de temps le fichier monté met à suivre. La boucle relit le
fichier toutes les 5 secondes, et s'arrête après 36 essais, soit 3 minutes,
même si rien ne change :

```bash
debut=$SECONDS; for i in $(seq 1 36); do kubectl exec courrier -n essai-secret -- grep -q port=465 /etc/relais/relais.conf 2>/dev/null && break; sleep 5; done; echo "attente : $((SECONDS - debut)) s"
kubectl exec courrier -n essai-secret -- cat /etc/relais/relais.conf
```

```text
attente : 81 s
serveur=smtp.exemple.fr
port=465
```

Le fichier a suivi tout seul, ici en 81 secondes. Lisez maintenant les
variables du même Pod, puis la valeur rangée dans le Secret. `base64 -d`
décode la valeur stockée :

```bash
kubectl exec courrier -n essai-secret -- sh -c 'echo MOT_DE_PASSE=$MOT_DE_PASSE SMTP_PASSWORD=$SMTP_PASSWORD'
kubectl get secret smtp-identifiants -n essai-secret -o jsonpath='{.data.SMTP_PASSWORD}' | base64 -d; echo
```

```text
MOT_DE_PASSE=Pluie-2026 SMTP_PASSWORD=Pluie-2026
Neige-2027
```

Le Secret dit `Neige-2027`, mais le conteneur voit toujours `Pluie-2026`, par
ses deux variables. Une variable se lit au démarrage du conteneur, puis reste
figée. Après un changement de mot de passe, une application qui lit ses
identifiants en variables garde l'ancien jusqu'au remplacement de son Pod.

## 🧹 Nettoyage

Supprimez les fichiers de travail et le namespace d'essai :

```bash
rm -f ~/relais.conf ~/courrier.yaml ~/doublon.yaml
kubectl delete namespace essai-secret
```

```text
namespace "essai-secret" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-configmap-secret-injection
dsoxlab check ckad-configmap-secret-injection
```

```text
╭─ Résultat : ckad-configmap-secret-injection ─╮
│  0 / 100 pts                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/14 tests            │
╰──────────────────────────────────────────────╯
```

0 sur 14 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : donner à une application ses réglages par un
ConfigMap et ses identifiants par un Secret, sans aucun mot de passe dans son
manifeste.

```bash
dsoxlab run ckad-configmap-secret-injection
dsoxlab challenge ckad-configmap-secret-injection
```
