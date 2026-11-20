# Surcharger les values d'un chart Helm

Un chart Helm se règle par ses **values** : le nombre de réplicas, une
couleur, un message. Le chart porte des valeurs par défaut, et vous les
**surchargez** (vous les remplacez) par un fichier ou à la ligne de commande.
Dans ce cours, vous comparez les values de deux versions d'un chart, vous
lisez les réglages d'une release posée par quelqu'un d'autre, vous voyez
comment `--set` devine le type d'une valeur, puis vous montez de version en
reprenant ces réglages, de deux façons.

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
20 novembre 2026, avec Kubernetes v1.37.2 et Helm 4.3.2.

## 📚 Exercice 1 : ce qu'une version ajoute aux values

`helm show values` affiche les values par défaut d'un chart, sans rien
installer. Comparez celles des versions 6.16.0 et 6.17.0 de podinfo :

```bash
diff <(helm show values podinfo/podinfo --version 6.16.0) <(helm show values podinfo/podinfo --version 6.17.0); echo "diff : code $?"
```

```text
11c11
<   tag: 6.16.0
---
>   tag: 6.17.0
98a99,103
>   # call the https backends with SPIFFE mTLS, presenting podinfo's SVID
>   backendMTLS: false
>   # the server SPIFFE IDs accepted from https backends, when empty any ID in podinfo's trust domain is accepted
>   # requires backendMTLS
>   backendIDs: []
diff : code 1
```

Deux changements. Le tag de l'image suit la version. Et 6.17.0 **ajoute**
deux values sous `spiffe`, `backendMTLS` et `backendIDs`, qui n'existaient
pas en 6.16.0. Retenez-les : l'exercice 7 montre qu'une montée de version peut
les oublier. Quelques values que vous allez changer :

```bash
helm show values podinfo/podinfo --version 6.17.0 | grep -n -E '^replicaCount|^ui:|^  color|^  message|^  logo'
```

```text
3:replicaCount: 1
17:ui:
18:  color: "#34577c"
19:  message: ""
20:  logo: ""
```

Les values sont rangées comme en YAML : `color` est **sous** `ui`, on l'écrit
donc `ui.color`. Par défaut : 1 réplica, une couleur bleue, pas de message.

## 📚 Exercice 2 : une release posée par quelqu'un d'autre

Un collègue installe une release avec ses réglages, passés à la ligne de
commande. Il ne laisse aucun fichier derrière lui :

```bash
kubectl create namespace essai-values
helm install vitrail podinfo/podinfo --version 6.16.0 -n essai-values --set replicaCount=2 --set ui.color=#2a9d8f --set ui.message=Bonjour --wait --timeout 180s | head -5
```

```text
namespace/essai-values created
NAME: vitrail
LAST DEPLOYED: Fri Nov 20 19:12:39 2026
NAMESPACE: essai-values
STATUS: deployed
REVISION: 1
```

Vous reprenez cette release. Les réglages ne sont nulle part sur le disque,
mais Helm les garde dans le cluster. `helm get values` montre les values que
la release a reçues :

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

Les trois valeurs du collègue ont remplacé les défauts. `logo`, que personne
n'a touché, garde le sien.

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

L'application applique bien ces values.

## 📚 Exercice 4 : --set devine le type

`--set` pose une value à la ligne de commande. `--reuse-values` garde les
values déjà passées. Changez le message en `1984`, sans changer de version :

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
2       	Fri Nov 20 19:12:41 2026	deployed  	podinfo-6.16.0	6.16.0     	Upgrade complete
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
même résultat.

## 📚 Exercice 6 : la montée qui perd les réglages, et leur reprise

Passez à la version 6.17.0 avec un nouveau message, sans rien d'autre :

```bash
helm upgrade vitrail podinfo/podinfo --version 6.17.0 -n essai-values --set-string ui.message=Salut --wait --timeout 180s > /dev/null; helm get values vitrail -n essai-values; kubectl get deployment vitrail-podinfo -n essai-values
```

```text
USER-SUPPLIED VALUES:
ui:
  message: Salut
NAME              READY   UP-TO-DATE   AVAILABLE   AGE
vitrail-podinfo   1/1     1            1           8s
```

Les 2 réplicas et la couleur ont disparu : retour à 1 réplica. Dès qu'un
`upgrade` reçoit une value, Helm repart des défauts du chart, plus les seules
values de cette commande. Les réglages du collègue ne sont pas perdus pour
autant : chaque révision garde les siens.

```bash
helm history vitrail -n essai-values | cut -c1-110
```

```text
REVISION	UPDATED                 	STATUS    	CHART         	APP VERSION	DESCRIPTION     
1       	Fri Nov 20 19:12:39 2026	superseded	podinfo-6.16.0	6.16.0     	Install complete
2       	Fri Nov 20 19:12:41 2026	superseded	podinfo-6.16.0	6.16.0     	Upgrade complete
3       	Fri Nov 20 19:12:44 2026	superseded	podinfo-6.16.0	6.16.0     	Upgrade complete
4       	Fri Nov 20 19:12:45 2026	deployed  	podinfo-6.17.0	6.17.0     	Upgrade complete
```

La révision 3 est la dernière qui portait les réglages complets. Enregistrez
ses values dans un fichier (`-o yaml` donne un fichier de values
réutilisable) :

```bash
helm get values vitrail -n essai-values --revision 3 -o yaml > ~/reprise.yaml; cat ~/reprise.yaml
```

```text
replicaCount: 2
ui:
  color: '#2a9d8f'
  message: "1984"
```

Repassez ce fichier avec `-f`, puis le nouveau message :

```bash
helm upgrade vitrail podinfo/podinfo --version 6.17.0 -n essai-values -f ~/reprise.yaml --set-string ui.message=Salut --wait --timeout 180s > /dev/null; helm get values vitrail -n essai-values; kubectl get deployment vitrail-podinfo -n essai-values
```

```text
USER-SUPPLIED VALUES:
replicaCount: 2
ui:
  color: '#2a9d8f'
  message: Salut
NAME              READY   UP-TO-DATE   AVAILABLE   AGE
vitrail-podinfo   2/2     2            2           11s
```

Le fichier redonne les 2 réplicas et la couleur. `--set-string`, lu après le
fichier, l'emporte pour le message : `Salut` remplace `1984`. Quand une value
est donnée deux fois, la dernière gagne. Et comme Helm est reparti des
défauts de la 6.17.0, les deux values ajoutées par cette version sont là :

```bash
helm get values vitrail -n essai-values --all | grep -n -E 'backend(MTLS|IDs)'
```

```text
171:  backendIDs: []
172:  backendMTLS: false
```

## 📚 Exercice 7 : --reuse-values ou --reset-then-reuse-values

Pourquoi ne pas simplement monter avec `--reuse-values` ? Revenez à la
révision 3, en 6.16.0, et vérifiez que les deux values de la 6.17.0 n'y sont
pas (`grep -c` compte les lignes trouvées) :

```bash
helm rollback vitrail 3 -n essai-values --wait --timeout 180s; helm get values vitrail -n essai-values --all | grep -c -E 'backend(MTLS|IDs)'
```

```text
Rollback was a success! Happy Helming!
0
```

Montez en 6.17.0 avec `--reuse-values` :

```bash
helm upgrade vitrail podinfo/podinfo --version 6.17.0 -n essai-values --reuse-values --set ui.message=Reprise --wait --timeout 180s > /dev/null; helm history vitrail -n essai-values | tail -1 | cut -c1-110; helm get values vitrail -n essai-values --all | grep -n -E 'backend(MTLS|IDs)'; echo "grep : code $?"
```

```text
7       	Fri Nov 20 19:12:53 2026	deployed  	podinfo-6.17.0	6.17.0     	Upgrade complete
grep : code 1
```

La release tourne en 6.17.0, mais `grep` ne trouve rien (code 1) : les deux
values ajoutées par la 6.17.0 manquent. `--reuse-values` reprend **toutes**
les values de la révision précédente, défauts de l'ancienne version compris,
et ignore ceux de la nouvelle. Ici, le chart s'en sort. Un autre chart, dont
un modèle lit une value nouvelle, peut échouer ou produire un manifeste faux.

`--reset-then-reuse-values` fait le tri : il repart des défauts de la
nouvelle version, puis y remet les seules values que la release avait reçues.
Revenez à la révision 3 et recommencez avec cette option :

```bash
helm rollback vitrail 3 -n essai-values --wait --timeout 180s > /dev/null; helm upgrade vitrail podinfo/podinfo --version 6.17.0 -n essai-values --reset-then-reuse-values --set ui.message=Reprise --wait --timeout 180s > /dev/null; helm history vitrail -n essai-values | tail -1 | cut -c1-110; helm get values vitrail -n essai-values
```

```text
9       	Fri Nov 20 19:13:18 2026	deployed  	podinfo-6.17.0	6.17.0     	Upgrade complete
USER-SUPPLIED VALUES:
replicaCount: 2
ui:
  color: '#2a9d8f'
  message: Reprise
```

Les réglages sont repris, et les nouvelles values de la 6.17.0 aussi :

```bash
helm get values vitrail -n essai-values --all | grep -n -E 'backend(MTLS|IDs)'
```

```text
171:  backendIDs: []
172:  backendMTLS: false
```

L'application tourne en 6.17.0 avec tous ses réglages (le `sleep` laisse le
temps aux anciens Pods de s'arrêter) :

```bash
sleep 10; IP=$(kubectl get service vitrail-podinfo -n essai-values -o jsonpath='{.spec.clusterIP}'); curl -s "http://$IP:9898" | grep -E '"(version|color|message)"'
```

```text
  "version": "6.17.0",
  "color": "#2a9d8f",
  "message": "Reprise",
```

## 🧹 Nettoyage

Désinstallez la release, supprimez son namespace et le fichier de reprise :

```bash
helm uninstall vitrail -n essai-values --wait; kubectl delete namespace essai-values; rm -f ~/reprise.yaml
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
