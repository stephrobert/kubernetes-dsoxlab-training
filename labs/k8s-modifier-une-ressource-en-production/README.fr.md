# Modifier un Deployment en production sans perdre un conteneur, et résorber la dérive

La leçon montre les façons de modifier un objet en place : `kubectl edit`,
`patch` et `replace`. Ce cours ajoute des cas que la leçon ne montre pas : le
même patch qui garde ou efface un conteneur selon son type, un patch JSON qui
vérifie une valeur avant de changer, un patch qui ne touche qu'au nombre de
réplicas, une édition refusée et la copie qu'elle laisse, et un `replace
--force` qui recrée l'objet.

Vous travaillez dans un namespace d'essai, `essai-modif`, avec un Deployment
`kiosque` à deux conteneurs : `vitre` (nginx) et `compteur` (busybox). Le
challenge porte sur un autre Deployment : vous le ferez seul, à la fin.

Page associée : [kubectl edit, patch et replace](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-edit-patch-replace/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-modifier-une-ressource-en-production
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Créez le namespace et le Deployment. La dernière commande affiche chaque
conteneur et son image, sans l'empreinte :

```bash
kubectl create namespace essai-modif; cat <<YAML | kubectl apply -n essai-modif -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kiosque
spec:
  replicas: 2
  selector:
    matchLabels: {app: kiosque}
  template:
    metadata:
      labels: {app: kiosque}
    spec:
      containers:
        - {name: vitre, image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb}
        - {name: compteur, image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4, command: [sleep, "3600"]}
YAML
kubectl rollout status deployment/kiosque -n essai-modif --timeout=120s; kubectl get deployment kiosque -n essai-modif -o jsonpath='{range .spec.template.spec.containers[*]}{.name}={.image} {end}{"\n"}' | sed 's/@sha256:[0-9a-f]*//g'
```

```text
namespace/essai-modif created
deployment.apps/kiosque created
Waiting for deployment "kiosque" rollout to finish: 0 out of 2 new replicas have been updated...
Waiting for deployment "kiosque" rollout to finish: 0 of 2 updated replicas are available...
Waiting for deployment "kiosque" rollout to finish: 1 of 2 updated replicas are available...
deployment "kiosque" successfully rolled out
vitre=nginx:1.30.5 compteur=busybox:1.38.0 
```

## ⚖️ Exercice 1 : le même patch, deux effets

Changez l'image de `vitre` avec un patch `strategic`, le type par défaut :

```bash
kubectl patch deployment kiosque -n essai-modif --type strategic -p '{"spec":{"template":{"spec":{"containers":[{"name":"vitre","image":"nginx:1.30"}]}}}}'; kubectl get deployment kiosque -n essai-modif -o jsonpath='{range .spec.template.spec.containers[*]}{.name}={.image} {end}{"\n"}' | sed 's/@sha256:[0-9a-f]*//g'
```

```text
deployment.apps/kiosque patched
vitre=nginx:1.30 compteur=busybox:1.38.0 
```

`vitre` a changé, `compteur` est toujours là. Le patch `strategic` connaît la
structure d'un Deployment : il retrouve le conteneur par son nom et ne
modifie que lui. Envoyez exactement le même contenu avec un patch `merge` :

```bash
kubectl patch deployment kiosque -n essai-modif --type merge -p '{"spec":{"template":{"spec":{"containers":[{"name":"vitre","image":"nginx:1.30"}]}}}}'; kubectl get deployment kiosque -n essai-modif -o jsonpath='{range .spec.template.spec.containers[*]}{.name}={.image} {end}{"\n"}' | sed 's/@sha256:[0-9a-f]*//g'
```

```text
deployment.apps/kiosque patched
vitre=nginx:1.30 
```

`compteur` a disparu. Un patch `merge` remplace une liste en entier : la
liste des conteneurs ne contient plus que `vitre`. Revenez à la révision
précédente :

```bash
kubectl rollout undo deployment/kiosque -n essai-modif >/dev/null; kubectl rollout status deployment/kiosque -n essai-modif --timeout=120s >/dev/null; kubectl get deployment kiosque -n essai-modif -o jsonpath='{range .spec.template.spec.containers[*]}{.name}={.image} {end}{"\n"}' | sed 's/@sha256:[0-9a-f]*//g'
```

```text
Warning: resource deployments/kiosque was previously managed with 'kubectl apply'. Rolling back will not update the kubectl.kubernetes.io/last-applied-configuration annotation, which may cause unexpected behavior on future 'kubectl apply' operations. Consider using 'kubectl apply' with your previous configuration file instead.
vitre=nginx:1.30 compteur=busybox:1.38.0 
```

Les deux conteneurs sont revenus. L'avertissement rappelle que l'annotation
de `kubectl apply` n'a pas suivi : un prochain `apply` du fichier d'origine
risque de surprendre. Pour modifier un conteneur dans une liste, le patch
`strategic` est le bon outil.

## 🔒 Exercice 2 : un patch JSON qui vérifie avant de changer

Un patch JSON peut commencer par une opération `test`, qui vérifie une valeur.
Si elle est fausse, rien n'est changé. Demandez de passer de 5 à 3 réplicas,
alors qu'il y en a 2 :

```bash
kubectl patch deployment kiosque -n essai-modif --type json -p '[{"op":"test","path":"/spec/replicas","value":5},{"op":"replace","path":"/spec/replicas","value":3}]'
```

```text
The request is invalid: the server rejected our request due to an error in our request
```

Refusé : le `test` a échoué, et le `replace` n'a pas été appliqué. Avec la
bonne valeur de départ :

```bash
kubectl patch deployment kiosque -n essai-modif --type json -p '[{"op":"test","path":"/spec/replicas","value":2},{"op":"replace","path":"/spec/replicas","value":3}]'; kubectl get deployment kiosque -n essai-modif -o jsonpath='réplicas={.spec.replicas}{"\n"}'
```

```text
deployment.apps/kiosque patched
réplicas=3
```

Accepté. Le `test` protège contre une modification faite par quelqu'un
d'autre entre le moment où vous avez lu l'objet et celui où vous le changez.

## 🔢 Exercice 3 : ne toucher qu'au nombre de réplicas

`--subresource=scale` envoie le patch au sous-objet `scale` du Deployment, qui
ne contient que le nombre de réplicas :

```bash
kubectl patch deployment kiosque -n essai-modif --subresource=scale --type merge -p '{"spec":{"replicas":4}}'; kubectl get deployment kiosque -n essai-modif -o jsonpath='réplicas={.spec.replicas}{"\n"}'
```

```text
scale.autoscaling/kiosque patched
réplicas=4
```

Le patch ne peut toucher à rien d'autre. C'est aussi ce qu'utilise `kubectl
scale`, et un droit RBAC sur `deployments/scale` suffit pour le faire.

## ✏️ Exercice 4 : une édition refusée

`kubectl edit` ouvre l'objet dans un éditeur. Ici, l'éditeur est remplacé par
un `sed` qui écrit une valeur invalide : `replicas: quatre`.

```bash
EDITOR='sed -i s/replicas:[[:space:]]4/replicas:\ quatre/' kubectl edit deployment kiosque -n essai-modif 2>&1 | tail -3
```

```text
error: deployments.apps "kiosque" is invalid
A copy of your changes has been stored to "/tmp/kubectl-edit-4194016663.yaml"
error: Edit cancelled, no valid changes were saved.
```

L'API refuse, et kubectl garde vos changements dans une copie sous `/tmp`.
Regardez-la :

```bash
ls -t /tmp/kubectl-edit-*.yaml 2>/dev/null | head -1 | xargs -r grep -m1 -n 'replicas: quatre'
```

```text
23:  replicas: quatre
```

La copie contient la ligne fautive. Avec un vrai éditeur, on corrige cette
copie et on l'applique, sans tout refaire.

## 💥 Exercice 5 : replace --force recrée l'objet

Exportez le Deployment, puis remplacez-le avec `--force`, et comparez son UID
avant et après :

```bash
kubectl get deployment kiosque -n essai-modif -o jsonpath='uid={.metadata.uid}{"\n"}'; kubectl get deployment kiosque -n essai-modif -o yaml > ~/kiosque.yaml; kubectl replace --force -f ~/kiosque.yaml; kubectl get deployment kiosque -n essai-modif -o jsonpath='uid={.metadata.uid}{"\n"}'
```

```text
uid=39db13d0-f702-4d2d-83e9-113c7882d038
deployment.apps "kiosque" deleted from essai-modif namespace
deployment.apps/kiosque replaced
uid=d4e31f4b-187c-4487-9417-5d96ca373e74
```

Un autre UID : `--force` supprime l'objet puis le recrée. Tous ses Pods ont
été remplacés, et tout ce qui le désignait par son UID est perdu. C'est le
dernier recours quand un champ immuable doit changer, pas une façon de
modifier un objet en production.

## 🧹 Nettoyage

Supprimez le namespace d'essai, le fichier exporté et la copie de l'édition :

```bash
kubectl delete namespace essai-modif; rm -f ~/kiosque.yaml /tmp/kubectl-edit-*.yaml
```

```text
namespace "essai-modif" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-modifier-une-ressource-en-production
dsoxlab check k8s-modifier-une-ressource-en-production
```

```text
╭─ Résultat : k8s-modifier-une-ressource-en-production ─╮
│  0 / 100 pts                                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                      │
╰───────────────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un Deployment de production à modifier sans perdre
son conteneur annexe, puis une dérive à résorber.

```bash
dsoxlab run k8s-modifier-une-ressource-en-production
dsoxlab challenge k8s-modifier-une-ressource-en-production
```
