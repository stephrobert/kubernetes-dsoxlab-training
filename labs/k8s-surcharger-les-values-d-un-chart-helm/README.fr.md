# Surcharger les values d'un chart Helm

Un chart Helm se règle par ses **values** : le nombre de réplicas, une
couleur, un message. Le chart porte des valeurs par défaut, et vous les
**surchargez** (vous les remplacez) par un fichier ou à la ligne de commande.
Dans ce cours, vous lisez les values par défaut d'un chart, vous installez avec
un fichier de values, vous lisez ce que répond l'application, vous voyez
comment `--set` devine le type d'une valeur, et vous montez de version sans
perdre vos réglages.

Vous travaillez avec une release d'essai, `vitrail`, du chart podinfo, dans un
namespace d'essai, `essai-values`. Le challenge porte sur une autre release :
vous le ferez seul, à la fin.

Page associée : [Les values Helm](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/helm/values/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-surcharger-les-values-d-un-chart-helm
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà, le lab a installé Helm
et déclaré le dépôt `podinfo`.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026, avec Kubernetes v1.37.2 et Helm 4.3.2.

## 📚 Exercice 1 : les values par défaut d'un chart

`helm show values` affiche les values par défaut d'un chart, sans rien
installer. `grep` en garde quelques-unes :

```bash
helm show values podinfo/podinfo --version 6.16.0 | grep -n -E '^replicaCount|^ui:|^  color|^  message|^  logo'
```

```text
3:replicaCount: 1
17:ui:
18:  color: "#34577c"
19:  message: ""
20:  logo: ""
```

Les values sont rangées comme en YAML : `color` est **sous** `ui`, on l'écrit
donc `ui.color`. Par défaut : 1 réplica, une couleur bleue, pas de message. Le
chart en propose bien d'autres :

```bash
helm show values podinfo/podinfo --version 6.16.0 | wc -l
```

```text
322
```

322 lignes. Vous n'en changez que quelques-unes, le reste garde sa valeur par
défaut.

## 📚 Exercice 2 : installer avec un fichier de values

Écrivez vos réglages dans un fichier : 2 réplicas, une couleur verte et un
message. Les guillemets autour de la couleur sont nécessaires : en YAML, un `#`
non protégé commence un commentaire.

```bash
mkdir -p ~/essai-values && cat > ~/essai-values/reglages.yaml <<'YAML'
replicaCount: 2
ui:
  color: "#2a9d8f"
  message: Bonjour
YAML
cat ~/essai-values/reglages.yaml
```

```text
replicaCount: 2
ui:
  color: "#2a9d8f"
  message: Bonjour
```

Créez le namespace d'essai, puis installez le chart avec ce fichier (`-f`) :

```bash
kubectl create namespace essai-values
helm install vitrail podinfo/podinfo --version 6.16.0 -n essai-values -f ~/essai-values/reglages.yaml --wait --timeout 180s | head -5
```

```text
namespace/essai-values created
NAME: vitrail
LAST DEPLOYED: Thu Nov 19 19:57:07 2026
NAMESPACE: essai-values
STATUS: deployed
REVISION: 1
```

`helm get values` montre les values que la release a reçues de vous :

```bash
helm get values vitrail -n essai-values
```

```text
USER-SUPPLIED VALUES:
replicaCount: 2
ui:
  color: '#2a9d8f'
  message: Bonjour
```

`--all` y ajoute toutes les values par défaut du chart, pour voir l'ensemble
de ce qui s'applique :

```bash
helm get values vitrail -n essai-values --all | grep -n -E '^replicaCount|^  color|^  message|^  logo'
```

```text
143:replicaCount: 2
181:  color: '#2a9d8f'
182:  logo: ""
183:  message: Bonjour
```

Vos trois valeurs ont remplacé les défauts. `logo`, que vous n'avez pas
touché, garde le sien.

## 📚 Exercice 3 : lire ce que répond l'application

podinfo répond sur le port 9898 de son Service, avec un petit document JSON.
`grep` garde la version, la couleur et le message :

```bash
IP=$(kubectl get service vitrail-podinfo -n essai-values -o jsonpath='{.spec.clusterIP}'); curl -s "http://$IP:9898" | grep -E '"(version|color|message)"'
```

```text
  "version": "6.16.0",
  "color": "#2a9d8f",
  "message": "Bonjour",
```

L'application applique bien vos values.

## 📚 Exercice 4 : --set devine le type

`--set` pose une value à la ligne de commande. `--reuse-values` garde les
values déjà passées. Changez le message en `1984` :

```bash
helm upgrade vitrail podinfo/podinfo --version 6.16.0 -n essai-values --reuse-values --set ui.message=1984 --wait --timeout 180s > /dev/null; echo "upgrade : code $?"
```

```text
upgrade : code 0
```

Lisez les values en JSON (`-o json`), qui montre le type de chaque valeur :

```bash
helm get values vitrail -n essai-values -o json; echo
```

```text
{"replicaCount":2,"ui":{"color":"#2a9d8f","message":1984}}
```

`"#2a9d8f"` est entre guillemets : c'est du texte. `1984` ne l'est pas :
`--set` a vu un nombre et l'a rangé comme un **entier**. De la même façon,
`--set` transforme `true` et `false` en booléens, et `null` en « aucune
valeur ». L'upgrade a pourtant réussi :

```bash
helm history vitrail -n essai-values | tail -1 | cut -c1-120
kubectl get deployment vitrail-podinfo -n essai-values -o jsonpath='{.spec.template.spec.containers[0].env}'; echo
```

```text
2       	Thu Nov 19 19:57:16 2026	deployed  	podinfo-6.16.0	6.16.0     	Upgrade complete
[{"name":"PODINFO_UI_MESSAGE","value":"1984"},{"name":"PODINFO_UI_COLOR","value":"#2a9d8f"}]
```

Ce chart remet la valeur en texte quand il écrit la variable d'environnement
du conteneur. Mais la release, elle, a gardé un entier : ce n'est pas ce que
vous vouliez écrire, et un autre chart pourrait s'en servir tel quel.

## 📚 Exercice 5 : --set-string garde une chaîne

`--set-string` pose la valeur comme du texte, quoi qu'elle contienne :

```bash
helm upgrade vitrail podinfo/podinfo --version 6.16.0 -n essai-values --reuse-values --set-string ui.message=1984 --wait --timeout 180s > /dev/null; echo "upgrade : code $?"
helm get values vitrail -n essai-values -o json; echo
```

```text
upgrade : code 0
{"replicaCount":2,"ui":{"color":"#2a9d8f","message":"1984"}}
```

Cette fois, `"1984"` est entre guillemets : c'est une chaîne. Un fichier de
values où la valeur est écrite entre guillemets (`message: "1984"`) donne le
même résultat. L'application affiche le message :

```bash
IP=$(kubectl get service vitrail-podinfo -n essai-values -o jsonpath='{.spec.clusterIP}'); curl -s "http://$IP:9898" | grep -E '"(version|color|message)"'
```

```text
  "version": "6.16.0",
  "color": "#2a9d8f",
  "message": "1984",
```

## 📚 Exercice 6 : monter de version sans perdre ses réglages

Passez à la version 6.17.0 du chart avec un nouveau message, **sans**
`--reuse-values` :

```bash
helm upgrade vitrail podinfo/podinfo --version 6.17.0 -n essai-values --set-string ui.message=Salut --wait --timeout 180s > /dev/null; helm get values vitrail -n essai-values; kubectl get deployment vitrail-podinfo -n essai-values
```

```text
USER-SUPPLIED VALUES:
ui:
  message: Salut
NAME              READY   UP-TO-DATE   AVAILABLE   AGE
vitrail-podinfo   1/1     1            1           29s
```

Les 2 réplicas et la couleur ont disparu : retour à 1 réplica. Dès qu'un
`upgrade` reçoit une value, Helm repart des défauts du chart, plus les seules
values de cette commande. Pour garder vos réglages, repassez le fichier de
values en plus du nouveau message :

```bash
helm upgrade vitrail podinfo/podinfo --version 6.17.0 -n essai-values -f ~/essai-values/reglages.yaml --set-string ui.message=Salut --wait --timeout 180s > /dev/null; helm get values vitrail -n essai-values; kubectl get deployment vitrail-podinfo -n essai-values
```

```text
USER-SUPPLIED VALUES:
replicaCount: 2
ui:
  color: '#2a9d8f'
  message: Salut
NAME              READY   UP-TO-DATE   AVAILABLE   AGE
vitrail-podinfo   2/2     2            2           41s
```

Le fichier redonne les 2 réplicas et la couleur. `--set-string`, lu après le
fichier, l'emporte pour le message : `Salut` remplace `Bonjour`. Quand une
value est donnée deux fois, la dernière gagne. L'application tourne en 6.17.0
avec tous vos réglages :

```bash
IP=$(kubectl get service vitrail-podinfo -n essai-values -o jsonpath='{.spec.clusterIP}'); curl -s "http://$IP:9898" | grep -E '"(version|color|message)"'
```

```text
  "version": "6.17.0",
  "color": "#2a9d8f",
  "message": "Salut",
```

## 🧹 Nettoyage

Désinstallez la release, supprimez son namespace et le fichier de values :

```bash
helm uninstall vitrail -n essai-values --wait; kubectl delete namespace essai-values; rm -rf ~/essai-values
```

```text
release "vitrail" uninstalled
namespace "essai-values" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-surcharger-les-values-d-un-chart-helm
dsoxlab check k8s-surcharger-les-values-d-un-chart-helm
```

```text
╭─ Résultat : k8s-surcharger-les-values-d-un-chart-helm ─╮
│  0 / 100 pts                                           │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests                       │
╰────────────────────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une autre release, réglée par quelqu'un d'autre.
Montez-la de version et changez son message, sans perdre ses réglages ni
tomber dans le piège du type.

```bash
dsoxlab run k8s-surcharger-les-values-d-un-chart-helm
dsoxlab challenge k8s-surcharger-les-values-d-un-chart-helm
```
