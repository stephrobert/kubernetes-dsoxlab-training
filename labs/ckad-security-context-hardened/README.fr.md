# Durcir un Pod avec un securityContext

La leçon montre le `securityContext` : l'utilisateur d'un conteneur,
l'interdiction de l'escalade de privilèges, une racine en lecture seule, les
capabilities retirées. Ce cours se concentre sur l'identité et l'escalade, et
ajoute des cas que la leçon ne montre pas : `runAsNonRoot` face à une image
qui tourne en root, `runAsUser` qui l'emporte sur l'image, une combinaison que
l'API refuse, et la preuve lue dans le noyau, par `/proc/1/status`.

Vous travaillez dans un namespace d'essai, `essai-identite`, avec des Pods
d'essai. Le challenge porte sur un autre Pod : vous le ferez seul, à la fin.

Page associée : [Security Context](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/security-context/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-security-context-hardened
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

## 🚫 Exercice 1 : runAsNonRoot face à une image qui tourne en root

`runAsNonRoot: true` demande au kubelet de refuser de démarrer un conteneur
qui tournerait en root. Créez le namespace et un Pod avec l'image agnhost,
qui ne déclare pas d'utilisateur et tourne donc en root :

```bash
kubectl create namespace essai-identite; kubectl run nomme --image=registry.k8s.io/e2e-test-images/agnhost:2.53 -n essai-identite --overrides='{"spec":{"securityContext":{"runAsNonRoot":true}}}' -- pause; sleep 10; kubectl get pod nomme -n essai-identite
```

```text
namespace/essai-identite created
pod/nomme created
NAME    READY   STATUS                       RESTARTS   AGE
nomme   0/1     CreateContainerConfigError   0          10s
```

Le Pod reste en `CreateContainerConfigError`. Lisez le message :

```bash
kubectl get pod nomme -n essai-identite -o jsonpath='{.status.containerStatuses[0].state.waiting.message}{"\n"}'
```

```text
container has runAsNonRoot and image will run as root (pod: "nomme_essai-identite(3c670f91-dd43-41c2-b343-b0cceaf4b224)", container: nomme)
```

Le kubelet a vérifié l'utilisateur que l'image utiliserait, et il a refusé.
`runAsNonRoot` ne change pas l'utilisateur : il empêche seulement de démarrer
en root. C'est un garde-fou, pas une correction.

## 🆔 Exercice 2 : donner l'identité dans le Pod

Gardez `runAsNonRoot`, et ajoutez `runAsUser` et `runAsGroup` au niveau du
Pod :

```bash
kubectl run chiffre --image=registry.k8s.io/e2e-test-images/agnhost:2.53 -n essai-identite --overrides='{"spec":{"securityContext":{"runAsNonRoot":true,"runAsUser":4242,"runAsGroup":4242}}}' -- pause; kubectl wait --for=condition=Ready pod/chiffre -n essai-identite --timeout=120s; kubectl exec chiffre -n essai-identite -- id
```

```text
pod/chiffre created
pod/chiffre condition met
uid=4242 gid=4242 groups=4242
```

Le Pod tourne, sous l'utilisateur et le groupe 4242. `runAsUser` l'emporte sur
ce que l'image prévoit, et `runAsNonRoot` est satisfait puisque 4242 n'est pas
0. L'utilisateur n'a pas besoin d'exister dans l'image : le noyau ne connaît
que des numéros.

## ⛔ Exercice 3 : une combinaison que l'API refuse

Créez un conteneur à la fois `privileged: true` et
`allowPrivilegeEscalation: false` :

```bash
kubectl run contradiction --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-identite --overrides='{"spec":{"containers":[{"name":"c","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"securityContext":{"privileged":true,"allowPrivilegeEscalation":false}}]}}' -- sleep 3600
```

```text
The Pod "contradiction" is invalid: spec.containers[0].securityContext: Invalid value: {"Capabilities":null,"Privileged":true,"SELinuxOptions":null,"WindowsOptions":null,"RunAsUser":null,"RunAsGroup":null,"RunAsNonRoot":null,"ReadOnlyRootFilesystem":null,"AllowPrivilegeEscalation":false,"ProcMount":null,"SeccompProfile":null,"AppArmorProfile":null}: cannot set `allowPrivilegeEscalation` to false and `privileged` to true
```

L'API refuse le Pod. La fin du message donne la raison : un conteneur
privilégié a déjà tous les droits, interdire l'escalade n'a donc pas de sens.
L'API préfère refuser une configuration contradictoire plutôt que d'en
ignorer une partie.

## 🔬 Exercice 4 : lire la preuve dans /proc

Le `securityContext` décrit une intention. Le noyau, lui, dit ce qui
s'applique vraiment. Créez un Pod avec `runAsUser: 2000`,
`allowPrivilegeEscalation: false` et toutes les capabilities retirées, puis
lisez l'état du processus principal :

```bash
kubectl run temoin --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-identite --overrides='{"spec":{"containers":[{"name":"c","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"securityContext":{"runAsUser":2000,"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]}}}]}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/temoin -n essai-identite --timeout=120s; kubectl exec temoin -n essai-identite -- grep -E '^(Uid|Gid|NoNewPrivs|CapEff|CapBnd)' /proc/1/status
```

```text
pod/temoin created
pod/temoin condition met
Uid:	2000	2000	2000	2000
Gid:	0	0	0	0
CapEff:	0000000000000000
CapBnd:	0000000000000000
NoNewPrivs:	1
```

`Uid` vaut 2000. `Gid` vaut 0 : sans `runAsGroup`, le groupe reste celui de
l'image, ici root. `CapEff` et `CapBnd` à zéro : aucune capability, ni
active ni récupérable. `NoNewPrivs: 1` est la traduction de
`allowPrivilegeEscalation: false` : le processus ne pourra jamais gagner de
droits, même par un programme setuid. Comparez avec un Pod sans
`securityContext` :

```bash
kubectl run ordinaire --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-identite -- sleep 3600; kubectl wait --for=condition=Ready pod/ordinaire -n essai-identite --timeout=120s; kubectl exec ordinaire -n essai-identite -- grep -E '^(Uid|NoNewPrivs|CapEff)' /proc/1/status
```

```text
pod/ordinaire created
pod/ordinaire condition met
Uid:	0	0	0	0
CapEff:	00000000a80425fb
NoNewPrivs:	0
```

Root, avec les capabilities par défaut du runtime (`a80425fb`), et
l'escalade permise. C'est l'état de départ de tout Pod qui ne demande rien.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-identite
```

```text
namespace "essai-identite" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-security-context-hardened
dsoxlab check ckad-security-context-hardened
```

```text
╭─ Résultat : ckad-security-context-hardened ─╮
│  0 / 100 pts                                │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests            │
╰─────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un serveur web à durcir, qui doit continuer à
répondre.

```bash
dsoxlab run ckad-security-context-hardened
dsoxlab challenge ckad-security-context-hardened
```
