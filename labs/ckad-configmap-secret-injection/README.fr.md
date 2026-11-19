# Donner des identifiants à une application avec un Secret

Un mot de passe ne doit pas être écrit dans le manifeste d'un Pod : ce
manifeste est versionné, relu, copié. Kubernetes range les valeurs sensibles
dans un objet à part, le **Secret**. Le Pod n'y fait qu'une **référence**, et
la valeur n'apparaît qu'à l'intérieur du conteneur, en variable
d'environnement ou en fichier. Dans ce cours, vous créez des Secrets, vous les
lisez, vous les donnez à une application de trois façons, et vous vérifiez ce
que le manifeste du Pod contient vraiment.

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
19 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : un Secret à partir de valeurs

Créez le namespace d'essai, puis un Secret `smtp-identifiants` avec deux
valeurs. Le type `generic` est le Secret ordinaire, qui range des paires
`clé=valeur` :

```bash
kubectl create namespace essai-secret
kubectl create secret generic smtp-identifiants --from-literal=SMTP_USER=courrier --from-literal=SMTP_PASSWORD='Pluie-2026' -n essai-secret
kubectl get secret smtp-identifiants -n essai-secret
```

```text
namespace/essai-secret created
secret/smtp-identifiants created
NAME                TYPE     DATA   AGE
smtp-identifiants   Opaque   2      0s
```

`Opaque` est le nom technique du type `generic`, et `DATA 2` compte ses deux
clés. `describe` les liste sans montrer leur valeur, seulement leur taille :

```bash
kubectl describe secret smtp-identifiants -n essai-secret | sed -n '/^Data/,$p'
```

```text
Data
====
SMTP_PASSWORD:  10 bytes
SMTP_USER:      8 bytes
```

## 📚 Exercice 2 : lire et décoder une valeur

`describe` cache les valeurs, mais elles restent lisibles par qui a le droit de
lire le Secret :

```bash
kubectl get secret smtp-identifiants -n essai-secret -o jsonpath='{.data}{"\n"}'
```

```text
{"SMTP_PASSWORD":"UGx1aWUtMjAyNg==","SMTP_USER":"Y291cnJpZXI="}
```

Les valeurs sont **encodées en base64**, une simple transformation, pas un
chiffrement. `base64 -d` les rend en clair (le `echo` ajoute le retour à la
ligne) :

```bash
kubectl get secret smtp-identifiants -n essai-secret -o jsonpath='{.data.SMTP_PASSWORD}' | base64 -d; echo
```

```text
Pluie-2026
```

Un Secret protège donc une valeur parce qu'elle vit **à part**, avec des droits
d'accès que l'on peut restreindre, et non parce qu'elle serait illisible.

## 📚 Exercice 3 : un Secret à partir d'un fichier

Comme un ConfigMap, un Secret peut porter un fichier entier. Le nom du fichier
devient la clé :

```bash
printf 'serveur=smtp.exemple.fr\nport=587\n' > ~/relais.conf; kubectl create secret generic smtp-relais --from-file=$HOME/relais.conf -n essai-secret
kubectl get secret smtp-relais -n essai-secret -o jsonpath='{.data}{"\n"}'
```

```text
secret/smtp-relais created
{"relais.conf":"c2VydmV1cj1zbXRwLmV4ZW1wbGUuZnIKcG9ydD01ODcK"}
```

## 📚 Exercice 4 : injecter une clé, ou toutes d'un coup

Le Pod `courrier` reçoit les Secrets de trois façons :

- `env` avec `secretKeyRef` : **une** clé, `SMTP_PASSWORD`, sous le nom de
  variable de votre choix, ici `MOT_DE_PASSE` ;
- `envFrom` avec `secretRef` : **toutes** les clés du Secret, chacune sous son
  propre nom ;
- un volume `secret`, monté sur `/etc/relais` : chaque clé de `smtp-relais` y
  devient un fichier, lisible par son seul propriétaire (`defaultMode: 0400`).

```bash
cat <<'YAML' | kubectl apply -n essai-secret -f -
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
kubectl wait --for=condition=Ready pod/courrier -n essai-secret --timeout=90s
```

```text
pod/courrier created
pod/courrier condition met
```

Lisez les variables depuis le conteneur :

```bash
kubectl exec courrier -n essai-secret -- sh -c 'echo MOT_DE_PASSE=$MOT_DE_PASSE; echo SMTP_USER=$SMTP_USER SMTP_PASSWORD=$SMTP_PASSWORD'
```

```text
MOT_DE_PASSE=Pluie-2026
SMTP_USER=courrier SMTP_PASSWORD=Pluie-2026
```

`MOT_DE_PASSE` vient de la référence clé par clé. `SMTP_USER` et
`SMTP_PASSWORD` viennent de `envFrom`, qui a repris les noms des clés.

## 📚 Exercice 5 : un Secret monté en fichiers

Regardez le dossier monté (`-L` montre le vrai fichier, pas le lien que
Kubernetes pose devant) :

```bash
kubectl exec courrier -n essai-secret -- ls -lL /etc/relais
kubectl exec courrier -n essai-secret -- cat /etc/relais/relais.conf
```

```text
total 4
-r--------    1 root     root            33 Nov 19 18:30 relais.conf
serveur=smtp.exemple.fr
port=587
```

Le fichier `relais.conf` est là, décodé, avec les droits `-r--------` :
lisible par son seul propriétaire, comme demandé par `defaultMode: 0400`.

## 📚 Exercice 6 : ce que le manifeste du Pod contient

Le but d'un Secret est de garder la valeur hors du manifeste. Vérifiez-le.
Voici les variables déclarées dans le Pod :

```bash
kubectl get pod courrier -n essai-secret -o jsonpath='{.spec.containers[0].env}{"\n"}'
```

```text
[{"name":"MOT_DE_PASSE","valueFrom":{"secretKeyRef":{"key":"SMTP_PASSWORD","name":"smtp-identifiants"}}}]
```

Une référence : un nom de Secret et un nom de clé, pas de valeur. Cherchez
enfin le mot de passe dans tout le manifeste du Pod :

```bash
kubectl get pod courrier -n essai-secret -o yaml | grep -c 'Pluie-2026'
```

```text
0
```

Zéro occurrence. Le mot de passe n'existe que dans le Secret, et dans le
conteneur qui en a besoin.

## 📚 Exercice 7 : une clé qui n'existe pas

Créez un Pod qui demande une clé absente du Secret, `SMTP_TOKEN` :

```bash
cat <<'YAML' | kubectl apply -n essai-secret -f -
apiVersion: v1
kind: Pod
metadata:
  name: cle-absente
spec:
  containers:
    - name: cle-absente
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "3600"]
      env:
        - name: JETON
          valueFrom:
            secretKeyRef:
              name: smtp-identifiants
              key: SMTP_TOKEN
YAML
sleep 8; kubectl get pod cle-absente -n essai-secret
```

```text
pod/cle-absente created
NAME          READY   STATUS                       RESTARTS   AGE
cle-absente   0/1     CreateContainerConfigError   0          8s
```

Le conteneur ne démarre pas. Les événements du Pod disent pourquoi :

```bash
kubectl get events -n essai-secret --field-selector involvedObject.name=cle-absente,type=Warning -o custom-columns=RAISON:.reason,MESSAGE:.message
```

```text
RAISON   MESSAGE
Failed   Error: couldn't find key SMTP_TOKEN in Secret essai-secret/smtp-identifiants
```

Le message nomme la clé et le Secret : vérifiez l'orthographe des deux.

## 🧹 Nettoyage

Supprimez le fichier de travail et le namespace d'essai :

```bash
rm -f ~/relais.conf; kubectl delete namespace essai-secret
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
