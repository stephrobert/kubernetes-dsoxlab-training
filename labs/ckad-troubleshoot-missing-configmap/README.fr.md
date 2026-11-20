# Un Pod bloqué par une ConfigMap qui n'existe pas

Un Pod peut attendre quelque chose avant même de démarrer son conteneur : une
ConfigMap, un Secret, une clé précise. Si ce quelque chose manque, le Pod reste
bloqué, et `kubectl logs` ne dit rien, puisque le conteneur n'existe pas
encore. Dans ce cours, vous bloquez un Pod sur une ConfigMap absente, vous
lisez la cause dans ses événements, vous le débloquez sans le recréer, puis
vous voyez trois variantes : une clé absente, une variable d'environnement qui
attend une ConfigMap, et une ConfigMap facultative.

Vous travaillez dans un namespace d'essai, `essai-panne`, avec les Pods
`accueil`, `cle-absente`, `variable` et `facultatif`. Le challenge porte sur un
autre Pod bloqué, dans un autre namespace : vous le dépannerez seul, à la fin.

Page associée : [Déboguer une application](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/debug-applications/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-troubleshoot-missing-configmap
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : un volume qui attend une ConfigMap absente

Créez le namespace d'essai et un Pod nginx `accueil`. Sa page d'accueil vient
d'un volume rempli par la ConfigMap `reglages-site`, qui n'existe pas :

```bash
kubectl create namespace essai-panne
cat <<'YAML' | kubectl apply -n essai-panne -f -
apiVersion: v1
kind: Pod
metadata:
  name: accueil
spec:
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      volumeMounts:
        - name: reglages
          mountPath: /usr/share/nginx/html
  volumes:
    - name: reglages
      configMap:
        name: reglages-site
YAML
```

```text
namespace/essai-panne created
pod/accueil created
```

15 secondes plus tard :

```bash
sleep 15; kubectl get pod accueil -n essai-panne
```

```text
NAME      READY   STATUS              RESTARTS   AGE
accueil   0/1     ContainerCreating   0          15s
```

`ContainerCreating` depuis 15 secondes. Les logs ?

```bash
kubectl logs accueil -n essai-panne 2>&1 | cut -c1-160
```

```text
Error from server (BadRequest): container "web" in pod "accueil" is waiting to start: ContainerCreating
```

Pas de logs : le conteneur n'existe pas encore. La cause se lit dans les
**événements** du Pod, en bas de `kubectl describe` :

```bash
kubectl describe pod accueil -n essai-panne | sed -n '/^Events:/,$p' | cut -c1-170
```

```text
Events:
  Type     Reason       Age               From               Message
  ----     ------       ----              ----               -------
  Normal   Scheduled    15s               default-scheduler  Successfully assigned essai-panne/accueil to k8s-w1.lab
  Warning  FailedMount  7s (x5 over 15s)  kubelet            MountVolume.SetUp failed for volume "reglages" : configmap "reglages-site" not found
```

`FailedMount` : le kubelet n'arrive pas à monter le volume `reglages`, parce
que la ConfigMap `reglages-site` n'existe pas. Il a déjà réessayé 5 fois.
Notez l'uid du Pod :

```bash
kubectl get pod accueil -n essai-panne -o jsonpath='uid={.metadata.uid}{"\n"}'
```

```text
uid=cf47334d-6359-4869-ad72-90c193dac868
```

## 📚 Exercice 2 : la ConfigMap arrive, le Pod repart seul

Créez la ConfigMap attendue. Sa clé `index.html` devient le fichier
`index.html` du volume :

```bash
kubectl create configmap reglages-site -n essai-panne --from-literal=index.html='bienvenue sur le site'
```

```text
configmap/reglages-site created
```

Ne touchez pas au Pod. Attendez simplement qu'il soit prêt :

```bash
kubectl wait --for=condition=Ready pod/accueil -n essai-panne --timeout=180s; kubectl get pod accueil -n essai-panne -o jsonpath='uid={.metadata.uid}{"\n"}'; kubectl get pod accueil -n essai-panne
```

```text
pod/accueil condition met
uid=cf47334d-6359-4869-ad72-90c193dac868
NAME      READY   STATUS    RESTARTS   AGE
accueil   1/1     Running   0          16s
```

Même uid : le Pod n'a pas été recréé. Le kubelet réessaie le montage tout seul,
et il a réussi dès que la ConfigMap a existé. La page est servie :

```bash
IP=$(kubectl get pod accueil -n essai-panne -o jsonpath='{.status.podIP}'); curl -s "http://$IP/"
```

```text
bienvenue sur le site
```

## 📚 Exercice 3 : une clé qui n'existe pas

La ConfigMap existe, mais le Pod `cle-absente` demande une clé précise,
`theme.css`, qu'elle ne contient pas (bloc `items`) :

```bash
cat <<'YAML' | kubectl apply -n essai-panne -f -
apiVersion: v1
kind: Pod
metadata:
  name: cle-absente
spec:
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      volumeMounts:
        - name: reglages
          mountPath: /config
  volumes:
    - name: reglages
      configMap:
        name: reglages-site
        items:
          - key: theme.css
            path: theme.css
YAML
```

```text
pod/cle-absente created
```

```bash
sleep 15; kubectl get pod cle-absente -n essai-panne; kubectl get events -n essai-panne --field-selector involvedObject.name=cle-absente,reason=FailedMount -o custom-columns=MESSAGE:.message --no-headers | sort -u | head -1 | cut -c1-170
```

```text
NAME          READY   STATUS              RESTARTS   AGE
cle-absente   0/1     ContainerCreating   0          15s
MountVolume.SetUp failed for volume "reglages" : configmap references non-existent config key: theme.css
```

Même blocage, autre message : la ConfigMap est là, mais la clé `theme.css`
manque. Lisez toujours le message en entier : c'est lui qui dit quoi réparer.

## 📚 Exercice 4 : une variable qui attend une ConfigMap absente

Le Pod `variable` lit une valeur de la ConfigMap `options-langue`, absente,
dans une **variable d'environnement** (`configMapKeyRef`) au lieu d'un volume :

```bash
cat <<'YAML' | kubectl apply -n essai-panne -f -
apiVersion: v1
kind: Pod
metadata:
  name: variable
spec:
  containers:
    - name: app
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo langue=$LANGUE; sleep 3600"]
      env:
        - name: LANGUE
          valueFrom:
            configMapKeyRef:
              name: options-langue
              key: langue
YAML
```

```text
pod/variable created
```

```bash
sleep 10; kubectl get pod variable -n essai-panne; kubectl get events -n essai-panne --field-selector involvedObject.name=variable,reason=Failed -o custom-columns=MESSAGE:.message --no-headers | sort -u | head -1
```

```text
NAME       READY   STATUS                       RESTARTS   AGE
variable   0/1     CreateContainerConfigError   0          10s
Error: configmap "options-langue" not found
```

Un autre état : `CreateContainerConfigError`. Le volume était monté par le
kubelet avant le conteneur (`ContainerCreating`). La variable, elle, sert à
préparer le conteneur, et c'est cette préparation qui échoue. Deux états
différents, une même cause : une ConfigMap absente.

## 📚 Exercice 5 : une ConfigMap facultative

`optional: true` dit à Kubernetes que la ConfigMap peut manquer, pour la
variable comme pour le volume :

```bash
cat <<'YAML' | kubectl apply -n essai-panne -f -
apiVersion: v1
kind: Pod
metadata:
  name: facultatif
spec:
  containers:
    - name: app
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo langue=$LANGUE; ls /extra; sleep 3600"]
      env:
        - name: LANGUE
          valueFrom:
            configMapKeyRef:
              name: options-langue
              key: langue
              optional: true
      volumeMounts:
        - name: extra
          mountPath: /extra
  volumes:
    - name: extra
      configMap:
        name: options-langue
        optional: true
YAML
kubectl wait --for=condition=Ready pod/facultatif -n essai-panne --timeout=120s
```

```text
pod/facultatif created
pod/facultatif condition met
```

```bash
kubectl get pod facultatif -n essai-panne; kubectl logs facultatif -n essai-panne
```

```text
NAME         READY   STATUS    RESTARTS   AGE
facultatif   1/1     Running   0          0s
langue=
```

Le Pod démarre : la variable est vide, et le répertoire `/extra` est vide
(`ls` n'affiche rien). Réservez `optional: true` à ce qui peut vraiment
manquer. Pour une configuration indispensable, mieux vaut un Pod bloqué
qu'une application qui démarre sans elle.

## 🧹 Nettoyage

Supprimez le namespace d'essai, avec ses Pods et sa ConfigMap :

```bash
kubectl delete namespace essai-panne
```

```text
namespace "essai-panne" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-troubleshoot-missing-configmap
dsoxlab check ckad-troubleshoot-missing-configmap
```

```text
╭─ Résultat : ckad-troubleshoot-missing-configmap ─╮
│  0 / 100 pts                                     │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                 │
╰──────────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un autre Pod, bloqué depuis une heure. Relevez la
cause dans ses événements avant de réparer quoi que ce soit.

```bash
dsoxlab run ckad-troubleshoot-missing-configmap
dsoxlab challenge ckad-troubleshoot-missing-configmap
```
