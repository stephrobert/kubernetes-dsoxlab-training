# Imposer un standard de sécurité aux Pods d'un namespace

La leçon montre les trois niveaux des Pod Security Standards et les trois
modes qui les appliquent à un namespace. Ce cours ajoute trois cas qu'elle ne
montre pas : un Pod que `baseline` laisse passer et que `restricted` refuse,
un Deployment accepté dont les Pods sont refusés, et la façon de savoir ce
qu'un niveau casserait **avant** de le poser.

Vous travaillez dans le namespace `essai-psa`. Le challenge porte sur un autre
namespace et d'autres Pods : vous le ferez seul, à la fin.

Page associée : [Pod Security Standards](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/pod-security-standards/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-pod-security-admission
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
22 novembre 2026, avec Kubernetes v1.37.2.

## 🪜 Exercice 1 : baseline laisse passer, restricted refuse

Créez un namespace au niveau `baseline`, et lancez-y un Pod ordinaire, qui
tourne en root sans aucun réglage de sécurité :

```bash
kubectl create namespace essai-psa; kubectl label namespace essai-psa pod-security.kubernetes.io/enforce=baseline; kubectl run ouvert --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-psa -- sleep 3600
```

```text
namespace/essai-psa created
namespace/essai-psa labeled
pod/ouvert created
```

Accepté : `baseline` refuse les gestes dangereux (Pod privilégié, accès aux
espaces de noms de l'hôte), pas un conteneur ordinaire en root. Montez
maintenant le namespace à `restricted`, et lancez un second Pod identique :

```bash
kubectl label namespace essai-psa pod-security.kubernetes.io/enforce=restricted --overwrite 2>&1; kubectl run ouvert-2 --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-psa -- sleep 3600 2>&1 | cut -c1-220
```

```text
Warning: existing pods in namespace "essai-psa" violate the new PodSecurity enforce level "restricted:latest"
Warning: ouvert: allowPrivilegeEscalation != false, unrestricted capabilities, runAsNonRoot != true, seccompProfile
namespace/essai-psa labeled
Error from server (Forbidden): pods "ouvert-2" is forbidden: violates PodSecurity "restricted:latest": allowPrivilegeEscalation != false (container "ouvert-2" must set securityContext.allowPrivilegeEscalation=false), unr
```

Deux choses à lire. Le label est posé, avec un avertissement : le Pod
`ouvert`, déjà là, viole le nouveau niveau, mais il **continue de tourner**.
L'admission ne juge que ce qui arrive, jamais ce qui existe. Le second Pod,
lui, est refusé, et le message énumère chaque champ en cause.

## 🏭 Exercice 2 : un Deployment accepté, des Pods refusés

Créez un Deployment dans ce namespace en `restricted` :

```bash
kubectl create deployment vitrine --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-psa -- sleep 3600; sleep 5; kubectl get deployment vitrine -n essai-psa
```

```text
Warning: would violate PodSecurity "restricted:latest": allowPrivilegeEscalation != false (container "busybox" must set securityContext.allowPrivilegeEscalation=false), unrestricted capabilities (container "busybox" must
deployment.apps/vitrine created
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
vitrine   0/1     0            0           5s
```

Le Deployment est créé, avec un simple avertissement, mais il reste à `0/1`.
L'admission ne refuse pas le Deployment : ce n'est pas un Pod. Ce sont les
Pods que son ReplicaSet essaie de créer qui sont refusés. L'erreur se lit dans
les événements du ReplicaSet :

```bash
kubectl describe replicaset -n essai-psa -l app=vitrine | sed -n '/Events:/,$p' | tail -1 | cut -c1-220
```

```text
  Warning  FailedCreate  2s    replicaset-controller  (combined from similar events): Error creating: pods "vitrine-84fc98bb46-r2hcf" is forbidden: violates PodSecurity "restricted:latest": allowPrivilegeEscalation != fa
```

`FailedCreate`, avec la même raison que pour un Pod créé à la main. Quand un
Deployment reste à 0 sans aucun Pod en erreur, regardez le ReplicaSet : c'est
le symptôme d'un refus à l'admission.

## 🔮 Exercice 3 : ce qu'un niveau casserait, avant de le poser

`--dry-run=server` fait juger une modification par l'API server sans
l'enregistrer. Appliqué à un label de niveau, il liste les Pods existants qui
seraient en infraction. Essayez-le sur `kube-system`, où vous ne poseriez
jamais `restricted` :

```bash
kubectl label --dry-run=server --overwrite namespace kube-system pod-security.kubernetes.io/enforce=restricted 2>&1 | cut -c1-160 | head -8
```

```text
Warning: existing pods in namespace "kube-system" violate the new PodSecurity enforce level "restricted:latest"
Warning: coredns-559f6c778d-bc5cl (and 1 other pod): runAsNonRoot != true, seccompProfile
Warning: etcd-k8s-cp.lab (and 3 other pods): host namespaces, hostPort, probe or lifecycle host, allowPrivilegeEscalation != false, unrestricted capabilities, r
Warning: kube-proxy-9fvg6 (and 2 other pods): host namespaces, privileged, allowPrivilegeEscalation != false, unrestricted capabilities, restricted volume types
namespace/kube-system labeled (server dry run)
```

Chaque ligne nomme un Pod et ce qui ne passerait pas : les composants du
control plane utilisent les espaces de noms de l'hôte, kube-proxy est
privilégié. La dernière ligne, `(server dry run)`, dit que rien n'a été
écrit. Vérifiez-le :

```bash
kubectl get namespace kube-system -o jsonpath='{.metadata.labels}{"\n"}'
```

```text
{"kubernetes.io/metadata.name":"kube-system"}
```

Aucun label de niveau sur `kube-system`. Lancez cette simulation sur chaque
namespace avant de l'encadrer, et vous savez d'avance quels Pods il faudra
corriger.

Enfin, un niveau peut être **épinglé** sur la version des règles d'une
version de Kubernetes, avec le label `enforce-version`. Le comportement ne
change plus quand le cluster est mis à jour :

```bash
kubectl label namespace essai-psa pod-security.kubernetes.io/enforce-version=v1.36 --overwrite; kubectl get namespace essai-psa -o jsonpath='{.metadata.labels}{"\n"}'
```

```text
Warning: existing pods in namespace "essai-psa" violate the new PodSecurity enforce level "restricted:v1.36"
Warning: ouvert: allowPrivilegeEscalation != false, unrestricted capabilities, runAsNonRoot != true, seccompProfile
namespace/essai-psa labeled
{"kubernetes.io/metadata.name":"essai-psa","pod-security.kubernetes.io/enforce":"restricted","pod-security.kubernetes.io/enforce-version":"v1.36"}
```

L'avertissement nomme désormais `restricted:v1.36` au lieu de
`restricted:latest`. `latest` suit les règles de la version du cluster, ce
qui peut faire refuser demain un Pod accepté aujourd'hui.

## 🧹 Nettoyage

Supprimez le namespace d'essai, avec le Pod et le Deployment qu'il contient :

```bash
kubectl delete namespace essai-psa
```

```text
namespace "essai-psa" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-pod-security-admission
dsoxlab check cks-pod-security-admission
```

```text
╭─ Résultat : cks-pod-security-admission ─╮
│  0 / 100 pts                            │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests        │
╰─────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un namespace à placer sous le standard `restricted`
dans les trois modes, et un Pod qui doit y tourner en le respectant.

```bash
dsoxlab run cks-pod-security-admission
dsoxlab challenge cks-pod-security-admission
```
