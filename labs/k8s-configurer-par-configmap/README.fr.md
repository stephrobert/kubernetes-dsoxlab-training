# Configurer une application avec un ConfigMap

Une bonne image de conteneur ne contient pas ses réglages : la même image sert
en test et en production, avec des réglages différents. Kubernetes range ces
réglages dans un objet à part, le **ConfigMap**, et les donne au conteneur en
**variables d'environnement** ou en **fichiers** dans un dossier. La leçon
montre `envFrom`, un volume, et ce qui se met à jour après une modification.
Ce cours va plus loin : donner à une variable un autre nom que sa clé, choisir
le nom d'un fichier monté, voir ce que cache `optional: true`, et changer de
configuration par un ConfigMap versionné.

Vous travaillez dans un namespace d'essai, `essai-config`, avec une
application `meteo`. Le challenge vous demandera de configurer une autre
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
20 novembre 2026.

## 📚 Exercice 1 : deux ConfigMaps

Créez le namespace d'essai et deux ConfigMaps :

- `meteo-reglages`, avec deux valeurs, dont les clés sont en minuscules :
  `ville` et `unite` ;
- `meteo-fichiers`, avec deux fichiers, `station.conf` et `alertes.conf`.
  Chaque `--from-file` ajoute un fichier, et son nom devient la clé.

```bash
kubectl create namespace essai-config
kubectl create configmap meteo-reglages --from-literal=ville=Lyon --from-literal=unite=celsius -n essai-config
printf 'station=lyon-bron\nfrequence=10\n' > ~/station.conf
printf 'seuil-vent=90\n' > ~/alertes.conf
kubectl create configmap meteo-fichiers --from-file=$HOME/station.conf --from-file=$HOME/alertes.conf -n essai-config
kubectl get configmap meteo-reglages meteo-fichiers -n essai-config
```

```text
namespace/essai-config created
configmap/meteo-reglages created
configmap/meteo-fichiers created
NAME             DATA   AGE
meteo-reglages   2      0s
meteo-fichiers   2      0s
```

La colonne `DATA` compte les clés : deux dans chaque ConfigMap.

## 📚 Exercice 2 : une variable qui ne porte pas le nom de sa clé

L'application `meteo` attend deux variables, `METEO_VILLE` et `METEO_UNITE`.
Les clés du ConfigMap s'appellent `ville` et `unite`. Avec `envFrom`, chaque
clé devient une variable **sous son nom exact** : vous obtiendriez `ville` et
`unite`, que l'application ne lit pas.

Le champ `env` avec `configMapKeyRef` donne le nom de votre choix : `name` est
le nom de la variable, `configMapKeyRef` dit quel ConfigMap et quelle clé la
remplissent. Le même Deployment monte aussi `meteo-fichiers`, ce que
l'exercice 3 détaille. Écrivez le manifeste dans un fichier, puis appliquez-le :

```bash
cat > ~/meteo.yaml <<'YAML'
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
          env:
            - name: METEO_VILLE
              valueFrom:
                configMapKeyRef:
                  name: meteo-reglages
                  key: ville
            - name: METEO_UNITE
              valueFrom:
                configMapKeyRef:
                  name: meteo-reglages
                  key: unite
          volumeMounts:
            - name: fichiers
              mountPath: /etc/meteo
            - name: fichiers
              mountPath: /etc/capteur.ini
              subPath: capteur.ini
      volumes:
        - name: fichiers
          configMap:
            name: meteo-fichiers
            items:
              - key: station.conf
                path: capteur.ini
YAML
kubectl apply -n essai-config -f ~/meteo.yaml
kubectl rollout status deployment/meteo -n essai-config --timeout=120s | tail -1
kubectl exec deploy/meteo -n essai-config -- env | grep -i -E 'ville|unite'
```

```text
deployment.apps/meteo created
deployment "meteo" successfully rolled out
METEO_VILLE=Lyon
METEO_UNITE=celsius
```

Les deux variables portent le nom attendu par l'application, et aucune
variable `ville` ou `unite` n'existe : `configMapKeyRef` ne crée que les
variables que vous nommez.

## 📚 Exercice 3 : choisir les fichiers montés et leur nom

Dans le volume, le champ `items` liste les clés à monter, et `path` donne le
nom du fichier. Ici, seule la clé `station.conf` est montée, sous le nom
`capteur.ini`. Regardez le dossier :

```bash
kubectl exec deploy/meteo -n essai-config -- ls /etc/meteo
kubectl exec deploy/meteo -n essai-config -- cat /etc/meteo/capteur.ini
```

```text
capteur.ini
station=lyon-bron
frequence=10
```

Un seul fichier, `capteur.ini`. `alertes.conf` n'est pas monté : avec `items`,
une clé absente de la liste n'apparaît pas dans le dossier.

Le Deployment monte aussi ce fichier une seconde fois, sur `/etc/capteur.ini`,
avec `subPath`. `subPath` nomme un chemin **dans le volume** : comme le volume
a renommé la clé, ce chemin est `capteur.ini`, et non `station.conf`.

## 📚 Exercice 4 : modifier, puis mesurer ce qui suit

Passez `unite` à `fahrenheit`, puis changez la fréquence dans `station.conf`
et remplacez `meteo-fichiers`. `--dry-run=client -o yaml` fabrique le nouveau
ConfigMap sans le créer, et `kubectl replace` remplace l'ancien. Les deux
fichiers sont redonnés : un ConfigMap remplacé ne garde que les clés que vous
lui passez.

```bash
kubectl patch configmap meteo-reglages -n essai-config -p '{"data":{"unite":"fahrenheit"}}'
printf 'station=lyon-bron\nfrequence=5\n' > ~/station.conf
kubectl create configmap meteo-fichiers --from-file=$HOME/station.conf --from-file=$HOME/alertes.conf -n essai-config --dry-run=client -o yaml | kubectl replace -f -
```

```text
configmap/meteo-reglages patched
configmap/meteo-fichiers replaced
```

Mesurez combien de temps le dossier met à se mettre à jour. La boucle relit
le fichier toutes les 5 secondes, et s'arrête après 36 essais, soit 3 minutes,
même si rien ne change :

```bash
debut=$SECONDS; for i in $(seq 1 36); do kubectl exec deploy/meteo -n essai-config -- grep -q frequence=5 /etc/meteo/capteur.ini 2>/dev/null && break; sleep 5; done; echo "attente : $((SECONDS - debut)) s"
```

```text
attente : 86 s
```

Le dossier s'est mis à jour **tout seul**, ici en 86 secondes : Kubernetes ne
relit les ConfigMaps qu'à intervalles réguliers. Le renommage par `items` ne
change rien à ce rafraîchissement. Comparez maintenant les trois endroits :

```bash
kubectl exec deploy/meteo -n essai-config -- cat /etc/meteo/capteur.ini /etc/capteur.ini
kubectl exec deploy/meteo -n essai-config -- printenv METEO_UNITE
```

```text
station=lyon-bron
frequence=5
station=lyon-bron
frequence=10
celsius
```

Le fichier du dossier dit `frequence=5`. Celui posé par `subPath` dit encore
`frequence=10`, et la variable dit encore `celsius`. Pour donner un nom choisi
à un fichier **et** garder la mise à jour, utilisez `items` plutôt que
`subPath`.

## 📚 Exercice 5 : une faute de frappe, avec et sans `optional`

Créez un Pod dont la variable vise `meteo-reglage`, sans le `s` final : ce
ConfigMap n'existe pas.

```bash
cat > ~/sans-config.yaml <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: sans-config
spec:
  terminationGracePeriodSeconds: 2
  containers:
    - name: sans-config
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "3600"]
      env:
        - name: METEO_UNITE
          valueFrom:
            configMapKeyRef:
              name: meteo-reglage
              key: unite
YAML
kubectl apply -n essai-config -f ~/sans-config.yaml
sleep 8; kubectl get pod sans-config -n essai-config
kubectl get pod sans-config -n essai-config -o jsonpath='{.status.containerStatuses[0].state.waiting.message}{"\n"}'
```

```text
pod/sans-config created
NAME          READY   STATUS                       RESTARTS   AGE
sans-config   0/1     CreateContainerConfigError   0          9s
configmap "meteo-reglage" not found
```

Le conteneur ne démarre pas, et le message nomme le ConfigMap introuvable. La
faute se voit tout de suite. Supprimez le Pod, ajoutez `optional: true` sous
`key: unite`, puis recréez-le :

```bash
kubectl delete pod sans-config -n essai-config
sed -i 's/key: unite/key: unite\n              optional: true/' ~/sans-config.yaml
grep -A4 configMapKeyRef ~/sans-config.yaml
kubectl apply -n essai-config -f ~/sans-config.yaml
kubectl wait --for=condition=Ready pod/sans-config -n essai-config --timeout=60s
kubectl exec sans-config -n essai-config -- sh -c 'echo METEO_UNITE=[$METEO_UNITE]'
```

```text
pod "sans-config" deleted from essai-config namespace
            configMapKeyRef:
              name: meteo-reglage
              key: unite
              optional: true
pod/sans-config created
pod/sans-config condition met
METEO_UNITE=[]
```

Le Pod démarre, et la variable n'existe pas : les crochets sont vides. La même
faute de frappe ne produit plus **aucune erreur**. `optional: true` convient à
un réglage vraiment facultatif. Ailleurs, il cache les erreurs de nom.

## 📚 Exercice 6 : changer de configuration par un ConfigMap versionné

Un ConfigMap `immutable: true` refuse toute modification. Pour changer de
configuration, on crée une nouvelle version sous un autre nom, et on fait
pointer le Deployment dessus. Créez `meteo-reglages-v2`, immuable, avec
l'unité `kelvin` :

```bash
cat > ~/meteo-v2.yaml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: meteo-reglages-v2
data:
  ville: Lyon
  unite: kelvin
immutable: true
YAML
kubectl apply -n essai-config -f ~/meteo-v2.yaml
```

```text
configmap/meteo-reglages-v2 created
```

Faites pointer les deux variables du Deployment sur `meteo-reglages-v2`.
`kubectl patch --type=json` remplace une valeur précise, désignée par son
chemin : `env/0` est la première variable, `env/1` la seconde. Le modèle de
Pod change, donc le Deployment remplace son Pod tout seul :

```bash
kubectl patch deployment meteo -n essai-config --type=json -p '[
  {"op": "replace", "path": "/spec/template/spec/containers/0/env/0/valueFrom/configMapKeyRef/name", "value": "meteo-reglages-v2"},
  {"op": "replace", "path": "/spec/template/spec/containers/0/env/1/valueFrom/configMapKeyRef/name", "value": "meteo-reglages-v2"}
]'
kubectl rollout status deployment/meteo -n essai-config --timeout=120s | tail -1
sleep 3; kubectl exec deploy/meteo -n essai-config -- printenv METEO_UNITE
```

```text
deployment.apps/meteo patched
deployment "meteo" successfully rolled out
kelvin
```

Pas besoin de `rollout restart` : changer de ConfigMap change le Deployment,
qui remplace ses Pods. Revenez maintenant à la version précédente du
Deployment :

```bash
kubectl rollout undo deployment/meteo -n essai-config
kubectl rollout status deployment/meteo -n essai-config --timeout=120s | tail -1
sleep 3; kubectl exec deploy/meteo -n essai-config -- printenv METEO_UNITE
```

```text
Warning: resource deployments/meteo was previously managed with 'kubectl apply'. Rolling back will not update the kubectl.kubernetes.io/last-applied-configuration annotation, which may cause unexpected behavior on future 'kubectl apply' operations. Consider using 'kubectl apply' with your previous configuration file instead.
deployment.apps/meteo rolled back
deployment "meteo" successfully rolled out
fahrenheit
```

Le Deployment pointe de nouveau sur `meteo-reglages`. Mais le Pod d'avant
voyait `celsius`, et le Pod rétabli voit `fahrenheit` : `meteo-reglages` a
été modifié à l'exercice 4. Le retour arrière rend le Deployment d'avant, pas
la configuration d'avant. Avec des ConfigMaps versionnés et immuables, chaque
version du Deployment retrouve exactement ses réglages.

L'avertissement dit que `rollout undo` ne met pas à jour l'annotation dont se
sert `kubectl apply`. Si vous réappliquez un jour `~/meteo.yaml`, c'est ce
fichier qui fera foi.

## 🧹 Nettoyage

Supprimez les fichiers de travail et le namespace d'essai :

```bash
rm -f ~/station.conf ~/alertes.conf ~/meteo.yaml ~/sans-config.yaml ~/meteo-v2.yaml
kubectl delete namespace essai-config
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
