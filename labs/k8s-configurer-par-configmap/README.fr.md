# Configurer une application avec un ConfigMap

Une bonne image de conteneur ne contient pas ses réglages : la même image sert
en test et en production, avec des réglages différents. Kubernetes range ces
réglages dans un objet à part, le **ConfigMap**, et les donne au conteneur de
deux façons : en **variables d'environnement**, ou en **fichiers** dans un
dossier. Dans ce cours, vous créez des ConfigMaps, vous les donnez à une
application, puis vous mesurez ce qui se met à jour, et quand, après une
modification.

Vous travaillez dans un namespace d'essai, `essai-config`, avec une application
`meteo`. Le challenge vous demandera le même travail sur une autre
application : vous le ferez seul, à la fin.

Page associée : [ConfigMaps Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/configmaps/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-configurer-par-configmap
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`boutique` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026.

## 📚 Exercice 1 : un ConfigMap à partir de valeurs

Créez le namespace d'essai, puis un ConfigMap `meteo-reglages` avec deux
valeurs. Chaque `--from-literal` ajoute une paire `clé=valeur` :

```bash
kubectl create namespace essai-config
kubectl create configmap meteo-reglages --from-literal=VILLE=Lyon --from-literal=UNITE=celsius -n essai-config
kubectl get configmap meteo-reglages -n essai-config -o jsonpath='{.data}{"\n"}'
```

```text
namespace/essai-config created
configmap/meteo-reglages created
{"UNITE":"celsius","VILLE":"Lyon"}
```

Les réglages sont rangés dans le champ `data` du ConfigMap.

## 📚 Exercice 2 : un ConfigMap à partir d'un fichier

Un réglage peut aussi être un fichier entier. Écrivez un petit fichier de
configuration, puis créez un ConfigMap à partir de lui avec `--from-file` :

```bash
printf 'station=lyon-bron\nfrequence=10\n' > ~/station.conf; cat ~/station.conf
kubectl create configmap meteo-fichier --from-file=$HOME/station.conf -n essai-config
kubectl describe configmap meteo-fichier -n essai-config | sed -n '/^Data/,/^BinaryData/p'
```

```text
station=lyon-bron
frequence=10
configmap/meteo-fichier created
Data
====
station.conf:
----
station=lyon-bron
frequence=10



BinaryData
```

Le **nom du fichier**, `station.conf`, est devenu la clé, et son contenu la
valeur. (`sed` ne garde que la partie `Data` de la sortie de `describe`.)

## 📚 Exercice 3 : donner les ConfigMaps à l'application

Le Deployment `meteo` reçoit les deux ConfigMaps, de trois façons :

- `envFrom` : chaque clé de `meteo-reglages` devient une variable
  d'environnement ;
- un volume monté **en dossier** sur `/etc/meteo` : chaque clé de
  `meteo-fichier` y devient un fichier ;
- le même volume, monté avec `subPath` sur `/etc/station.conf` : un seul
  fichier, posé à un endroit précis.

Son conteneur ne fait que dormir : on vient seulement lire ce qu'il voit.

```bash
cat <<'YAML' | kubectl apply -n essai-config -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meteo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: meteo
  template:
    metadata:
      labels:
        app: meteo
    spec:
      terminationGracePeriodSeconds: 2
      containers:
        - name: meteo
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sleep", "86400"]
          envFrom:
            - configMapRef:
                name: meteo-reglages
          volumeMounts:
            - name: fichier
              mountPath: /etc/meteo
            - name: fichier
              mountPath: /etc/station.conf
              subPath: station.conf
      volumes:
        - name: fichier
          configMap:
            name: meteo-fichier
YAML
kubectl rollout status deployment/meteo -n essai-config --timeout=120s | tail -1
```

```text
deployment.apps/meteo created
deployment "meteo" successfully rolled out
```

Vérifiez toujours depuis le conteneur : la spécification dit ce qui est
demandé, le conteneur dit ce qui est vu. `kubectl exec deploy/meteo` entre dans
un Pod du Deployment :

```bash
kubectl exec deploy/meteo -n essai-config -- sh -c 'echo VILLE=$VILLE UNITE=$UNITE'
kubectl exec deploy/meteo -n essai-config -- ls /etc/meteo
kubectl exec deploy/meteo -n essai-config -- cat /etc/meteo/station.conf /etc/station.conf
```

```text
VILLE=Lyon UNITE=celsius
station.conf
station=lyon-bron
frequence=10
station=lyon-bron
frequence=10
```

Les deux variables sont là, et le fichier aussi, aux deux endroits.

## 📚 Exercice 4 : changer une valeur

Passez `UNITE` à `fahrenheit` dans le ConfigMap :

```bash
kubectl patch configmap meteo-reglages -n essai-config -p '{"data":{"UNITE":"fahrenheit"}}'
kubectl get configmap meteo-reglages -n essai-config -o jsonpath='{.data.UNITE}{"\n"}'
kubectl exec deploy/meteo -n essai-config -- sh -c 'echo UNITE=$UNITE'
```

```text
configmap/meteo-reglages patched
fahrenheit
UNITE=celsius
```

Le ConfigMap dit `fahrenheit`, mais le conteneur voit toujours `celsius`. Une
variable d'environnement se lit **une seule fois**, au démarrage du conteneur.
Ensuite, elle reste figée.

## 📚 Exercice 5 : changer le fichier

Modifiez le fichier, puis remplacez le ConfigMap par la nouvelle version.
`--dry-run=client -o yaml` fabrique le nouveau ConfigMap sans le créer, et
`kubectl replace` remplace l'ancien :

```bash
printf 'station=lyon-bron\nfrequence=5\n' > ~/station.conf; kubectl create configmap meteo-fichier --from-file=$HOME/station.conf -n essai-config --dry-run=client -o yaml | kubectl replace -f -
```

```text
configmap/meteo-fichier replaced
```

Mesurez combien de temps le dossier met à se mettre à jour. La boucle relit le
fichier toutes les 5 secondes, jusqu'à y trouver `frequence=5` :

```bash
debut=$SECONDS; until kubectl exec deploy/meteo -n essai-config -- grep -q frequence=5 /etc/meteo/station.conf 2>/dev/null; do sleep 5; done; echo "dossier à jour après $((SECONDS - debut)) s"
```

```text
dossier à jour après 71 s
```

Le dossier se met à jour **tout seul**, mais avec un délai, ici 71 secondes :
Kubernetes ne relit les ConfigMaps qu'à intervalles réguliers. Comparez
maintenant les deux emplacements :

```bash
kubectl exec deploy/meteo -n essai-config -- cat /etc/meteo/station.conf /etc/station.conf
```

```text
station=lyon-bron
frequence=5
station=lyon-bron
frequence=10
```

Le fichier du dossier dit `frequence=5`. Celui posé par `subPath` dit encore
`frequence=10` : un montage par `subPath` ne se met **jamais** à jour.

## 📚 Exercice 6 : redémarrer pour tout relire

`kubectl rollout restart` remplace les Pods du Deployment. Les nouveaux
conteneurs relisent tout au démarrage :

```bash
kubectl rollout restart deployment/meteo -n essai-config
kubectl rollout status deployment/meteo -n essai-config --timeout=120s | tail -1
sleep 3; kubectl exec deploy/meteo -n essai-config -- sh -c 'echo UNITE=$UNITE; cat /etc/station.conf'
```

```text
deployment.apps/meteo restarted
deployment "meteo" successfully rolled out
UNITE=fahrenheit
station=lyon-bron
frequence=5
```

La variable et le fichier `subPath` sont enfin à jour. Retenez la règle :

| Où arrive le réglage | Après une modification du ConfigMap |
|---|---|
| Variable d'environnement | rien ne change, jusqu'au redémarrage |
| Dossier monté | mis à jour tout seul, avec un délai |
| Fichier `subPath` | rien ne change, jusqu'au redémarrage |

## 📚 Exercice 7 : un ConfigMap qui manque

Que se passe-t-il si un Pod demande un ConfigMap qui n'existe pas ? Créez un
Pod qui attend `meteo-absent` :

```bash
cat <<'YAML' | kubectl apply -n essai-config -f -
apiVersion: v1
kind: Pod
metadata:
  name: sans-config
spec:
  containers:
    - name: sans-config
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "3600"]
      envFrom:
        - configMapRef:
            name: meteo-absent
YAML
sleep 8; kubectl get pod sans-config -n essai-config
```

```text
pod/sans-config created
NAME          READY   STATUS                       RESTARTS   AGE
sans-config   0/1     CreateContainerConfigError   0          8s
```

Le conteneur ne démarre pas : `CreateContainerConfigError`. Les événements du
Pod de type `Warning` disent pourquoi :

```bash
kubectl get events -n essai-config --field-selector involvedObject.name=sans-config,type=Warning -o custom-columns=RAISON:.reason,MESSAGE:.message
```

```text
RAISON   MESSAGE
Failed   Error: configmap "meteo-absent" not found
```

D'où la règle pratique : créez les ConfigMaps **avant** les Pods qui en ont
besoin.

## 🧹 Nettoyage

Supprimez le fichier de travail et le namespace d'essai :

```bash
rm -f ~/station.conf; kubectl delete namespace essai-config
```

```text
namespace "essai-config" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-configurer-par-configmap
dsoxlab check k8s-configurer-par-configmap
```

```text
╭─ Résultat : k8s-configurer-par-configmap ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests          │
╰───────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : configurer une application avec deux ConfigMaps,
puis faire passer une modification jusqu'au conteneur.

```bash
dsoxlab run k8s-configurer-par-configmap
dsoxlab challenge k8s-configurer-par-configmap
```
