# Valider et modifier à l'admission

La leçon montre où passent les admission controllers, quels contrôleurs sont
actifs par défaut, comment une MutatingAdmissionPolicy et une
ValidatingAdmissionPolicy agissent sans webhook, et comment diagnostiquer un
webhook qui ne répond pas. Ce cours vous fait faire chacun de ces gestes sur
le cluster, avec d'autres règles que celles du challenge : un label `cours`,
une interdiction de `hostPID` et un webhook sur les ConfigMaps.

Vous travaillez dans les namespaces `essai-admission` et `essai-temoin`. Le
challenge porte sur d'autres namespaces et d'autres règles : vous le ferez
seul, à la fin.

Page associée : [Admission Controllers Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/admission-controllers/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-valider-et-modifier-a-l-admission
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
23 novembre 2026, avec Kubernetes v1.37.2.

## 📋 Exercice 1 : reconstituer la liste des contrôleurs actifs

Le manifeste de l'API server ne donne qu'une partie de la liste. Lisez-le,
puis extrayez de l'aide du binaire la liste des contrôleurs activés par
défaut, et rangez-la dans un fichier :

```bash
sudo grep admission-plugins /etc/kubernetes/manifests/kube-apiserver.yaml
kubectl -n kube-system exec kube-apiserver-k8s-cp.lab -- kube-apiserver --help 2>/dev/null \
  | grep -o 'default enabled ones ([^)]*)' | cut -d'(' -f2 | tr -d ') ' | tr ',' '\n' > defaut.txt
wc -l < defaut.txt
grep -c -x NodeRestriction defaut.txt
grep -x -e PodSecurity -e MutatingAdmissionPolicy -e ValidatingAdmissionPolicy defaut.txt
```

```text
    - --enable-admission-plugins=NodeRestriction
25
0
PodSecurity
MutatingAdmissionPolicy
ValidatingAdmissionPolicy
```

Le manifeste n'active que `NodeRestriction`, mais ce drapeau **ajoute** à la
liste par défaut, il ne la remplace pas. La liste par défaut compte 25
contrôleurs, et `NodeRestriction` n'en fait pas partie : c'est pour cela que
kubeadm l'ajoute. Les trois contrôleurs de la dernière commande sont actifs
sans rien installer. Ce sont eux qui servent dans la suite du cours.

## 🔀 Exercice 2 : la mutation passe avant la validation

Créez le namespace d'essai et une ValidatingAdmissionPolicy qui exige le label
`cours` sur chaque Pod créé dans `essai-admission`. Testez-la avec
`--dry-run=server` : la requête traverse toute l'admission, mais rien n'est
enregistré.

```bash
kubectl create namespace essai-admission; cat <<'YAML' | kubectl apply -f -
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: essai-exige-cours
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE]
        resources: [pods]
  validations:
    - expression: 'has(object.metadata.labels) && "cours" in object.metadata.labels'
      message: "un Pod de essai-admission porte le label cours"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: essai-exige-cours
spec:
  policyName: essai-exige-cours
  validationActions: [Deny]
  matchResources:
    namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: essai-admission
YAML
sleep 5; kubectl -n essai-admission run essai-a --image=busybox:1.37 --restart=Never --dry-run=server -- sleep 60
```

```text
namespace/essai-admission created
validatingadmissionpolicy.admissionregistration.k8s.io/essai-exige-cours created
validatingadmissionpolicybinding.admissionregistration.k8s.io/essai-exige-cours created
The pods "essai-a" is invalid: : ValidatingAdmissionPolicy 'essai-exige-cours' with binding 'essai-exige-cours' denied request: un Pod de essai-admission porte le label cours
```

Le Pod est refusé : `kubectl run` ne pose que le label `run`. Ajoutez
maintenant une MutatingAdmissionPolicy qui pose `cours: admission` sur les
Pods du même namespace, puis soumettez le même Pod :

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionPolicy
metadata:
  name: essai-pose-cours
spec:
  failurePolicy: Fail
  reinvocationPolicy: Never
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE]
        resources: [pods]
  mutations:
    - patchType: ApplyConfiguration
      applyConfiguration:
        expression: |
          Object{
            metadata: Object.metadata{
              labels: {"cours": "admission"}
            }
          }
---
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionPolicyBinding
metadata:
  name: essai-pose-cours
spec:
  policyName: essai-pose-cours
  matchResources:
    namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: essai-admission
YAML
sleep 5; kubectl -n essai-admission run essai-a --image=busybox:1.37 --restart=Never --dry-run=server -o jsonpath='{.metadata.labels}{"\n"}' -- sleep 60
```

```text
mutatingadmissionpolicy.admissionregistration.k8s.io/essai-pose-cours created
mutatingadmissionpolicybinding.admissionregistration.k8s.io/essai-pose-cours created
{"cours":"admission","run":"essai-a"}
```

Le même Pod passe, et il porte le label `cours`. La mutation s'exécute avant
la validation : quand la VAP regarde le Pod, le label est déjà posé.

## 🧩 Exercice 3 : ce que la fusion garde et ce qu'elle écrase

La MAP décrit un objet partiel que l'API server fusionne avec le Pod.
Soumettez un Pod qui déclare déjà deux labels, dont `cours` avec une autre
valeur :

```bash
kubectl -n essai-admission run essai-b --image=busybox:1.37 --restart=Never --labels=cours=autre,app=demo --dry-run=server -o jsonpath='{.metadata.labels}{"\n"}' -- sleep 60
```

```text
{"app":"demo","cours":"admission"}
```

Le label `app` est gardé : la MAP ne le mentionne pas. Le label `cours`, lui,
est **écrasé** par la valeur de la MAP. Une MAP écrite ainsi impose une
valeur, elle ne la complète pas seulement quand elle manque.

## 🚫 Exercice 4 : une règle qui ne s'applique qu'aux namespaces étiquetés

Créez un namespace témoin, puis une VAP qui refuse les Pods en `hostPID` (qui
voient les processus du nœud). Son binding choisit les namespaces par le label
`environment=essai`, que personne n'a encore posé. Préparez un Pod en
`hostPID` et soumettez-le :

```bash
kubectl create namespace essai-temoin; cat <<'YAML' | kubectl apply -f -
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: essai-sans-hostpid
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE, UPDATE]
        resources: [pods]
  validations:
    - expression: '!(has(object.spec.hostPID) && object.spec.hostPID)'
      message: "hostPID est interdit ici"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: essai-sans-hostpid
spec:
  policyName: essai-sans-hostpid
  validationActions: [Deny]
  matchResources:
    namespaceSelector:
      matchLabels:
        environment: essai
YAML
cat > hostpid.yaml <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: essai-hostpid
  labels:
    cours: admission
spec:
  hostPID: true
  containers:
    - name: c
      image: busybox:1.37
      command: ["sleep", "60"]
YAML
sleep 5; kubectl -n essai-admission apply -f hostpid.yaml --dry-run=server
```

```text
namespace/essai-temoin created
validatingadmissionpolicy.admissionregistration.k8s.io/essai-sans-hostpid created
validatingadmissionpolicybinding.admissionregistration.k8s.io/essai-sans-hostpid created
pod/essai-hostpid created (server dry run)
```

La politique et son binding existent, et le Pod passe quand même : aucun
namespace ne porte le label `environment=essai`. Posez-le sur
`essai-admission`, puis soumettez le Pod dans les deux namespaces :

```bash
kubectl label namespace essai-admission environment=essai
sleep 5; kubectl -n essai-admission apply -f hostpid.yaml --dry-run=server
kubectl -n essai-temoin apply -f hostpid.yaml --dry-run=server
```

```text
namespace/essai-admission labeled
The pods "essai-hostpid" is invalid: : ValidatingAdmissionPolicy 'essai-sans-hostpid' with binding 'essai-sans-hostpid' denied request: hostPID est interdit ici
pod/essai-hostpid created (server dry run)
```

Refusé dans `essai-admission`, accepté dans `essai-temoin`. Le message nomme
la politique et le binding : c'est par eux que vous remontez à la règle.

## 🩺 Exercice 5 : diagnostiquer un webhook qui ne répond pas

Créez un Service `essai-controleur` sans aucun Pod derrière lui, puis un
webhook de validation qui l'appelle pour chaque ConfigMap créée dans
`essai-admission`, avec `failurePolicy: Fail`. Essayez de créer une
ConfigMap :

```bash
kubectl -n essai-admission create service clusterip essai-controleur --tcp=443:8443
cat <<'YAML' | kubectl apply -f -
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: essai-controle-configmaps
webhooks:
  - name: controle.essai-admission.svc
    clientConfig:
      service:
        name: essai-controleur
        namespace: essai-admission
        path: /valider
    rules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE]
        resources: [configmaps]
    namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: essai-admission
    admissionReviewVersions: [v1]
    sideEffects: None
    failurePolicy: Fail
YAML
sleep 3; kubectl -n essai-admission create configmap essai-cm --from-literal=a=1
```

```text
service/essai-controleur created
validatingwebhookconfiguration.admissionregistration.k8s.io/essai-controle-configmaps created
error: failed to create configmap: Internal error occurred: failed calling webhook "controle.essai-admission.svc": failed to call webhook: Post "https://essai-controleur.essai-admission.svc:443/valider?timeout=10s": dial tcp 10.97.18.97:443: connect: connection refused
```

Le message donne le nom du **webhook**, `controle.essai-admission.svc`, et
l'adresse du Service appelé, `essai-controleur.essai-admission.svc`. Il ne
donne pas le nom de la **configuration** qui le porte, et c'est elle qu'il
faudra modifier. Remontez du message à la cause : cherchez quelle
configuration contient ce webhook, lisez son `failurePolicy` et son Service,
puis regardez les endpoints de ce Service.

```bash
kubectl get validatingwebhookconfigurations -o custom-columns='CONFIGURATION:.metadata.name,WEBHOOKS:.webhooks[*].name,ECHEC:.webhooks[*].failurePolicy,SERVICE:.webhooks[*].clientConfig.service.name' | grep -e CONFIGURATION -e controle.essai-admission.svc
kubectl -n essai-admission get endpointslice -l kubernetes.io/service-name=essai-controleur
```

```text
CONFIGURATION                  WEBHOOKS                       ECHEC   SERVICE
essai-controle-configmaps      controle.essai-admission.svc   Fail    essai-controleur
NAME                     ADDRESSTYPE   PORTS     ENDPOINTS   AGE
essai-controleur-9hzdv   IPv4          <unset>   <unset>     3s
```

La configuration s'appelle `essai-controle-configmaps`. Son webhook est en
`Fail` et son Service n'a aucun endpoint (`<unset>`) : aucun Pod ne peut
répondre, donc toute ConfigMap de ce namespace est refusée. Passez le webhook en `Ignore` et recommencez :

```bash
kubectl patch validatingwebhookconfiguration essai-controle-configmaps --type=json -p '[{"op":"replace","path":"/webhooks/0/failurePolicy","value":"Ignore"}]'
sleep 3; kubectl -n essai-admission create configmap essai-cm --from-literal=a=1
kubectl -n kube-system logs kube-apiserver-k8s-cp.lab --since=60s | grep -o 'Failed calling webhook, failing open [^:]*' | tail -1
```

```text
validatingwebhookconfiguration.admissionregistration.k8s.io/essai-controle-configmaps patched
configmap/essai-cm created
Failed calling webhook, failing open controle.essai-admission.svc
```

La ConfigMap est créée sans un mot côté client. Le webhook n'a pourtant rien
vérifié : seul le journal de l'API server le dit (`failing open`). C'est le
piège de `Ignore`.

## 🧹 Nettoyage

Les webhooks, les politiques et leurs bindings appartiennent au cluster, pas à
un namespace : supprimez-les un par un, puis les deux namespaces d'essai et le
fichier préparé à l'exercice 4. La dernière commande compte les objets
`essai` qui restent :

```bash
kubectl delete validatingwebhookconfiguration essai-controle-configmaps
kubectl delete validatingadmissionpolicybinding essai-exige-cours essai-sans-hostpid
kubectl delete validatingadmissionpolicy essai-exige-cours essai-sans-hostpid
kubectl delete mutatingadmissionpolicybinding essai-pose-cours
kubectl delete mutatingadmissionpolicy essai-pose-cours
kubectl delete namespace essai-admission essai-temoin --wait=true --timeout=120s
rm -f defaut.txt hostpid.yaml
kubectl get validatingadmissionpolicy,mutatingadmissionpolicy,validatingwebhookconfiguration -o name | grep -c essai
```

```text
validatingwebhookconfiguration.admissionregistration.k8s.io "essai-controle-configmaps" deleted
validatingadmissionpolicybinding.admissionregistration.k8s.io "essai-exige-cours" deleted
validatingadmissionpolicybinding.admissionregistration.k8s.io "essai-sans-hostpid" deleted
validatingadmissionpolicy.admissionregistration.k8s.io "essai-exige-cours" deleted
validatingadmissionpolicy.admissionregistration.k8s.io "essai-sans-hostpid" deleted
mutatingadmissionpolicybinding.admissionregistration.k8s.io "essai-pose-cours" deleted
mutatingadmissionpolicy.admissionregistration.k8s.io "essai-pose-cours" deleted
namespace "essai-admission" deleted
namespace "essai-temoin" deleted
0
```

Plus aucun objet d'essai. Quittez ensuite la machine et remettez le lab à
zéro. `dsoxlab reset` rejoue le nettoyage puis la préparation du lab : vous
retrouvez exactement l'état de départ du challenge. Il vous demande de
confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-valider-et-modifier-a-l-admission
dsoxlab check k8s-valider-et-modifier-a-l-admission
```

```text
╭─ Résultat : k8s-valider-et-modifier-a-l-admission ─╮
│  0 / 100 pts                                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests                   │
╰────────────────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : débloquer un namespace où plus aucun Pod ne se crée,
puis y faire poser un label par défaut et refuser les conteneurs privilégiés
par l'API server lui-même.

```bash
dsoxlab run k8s-valider-et-modifier-a-l-admission
dsoxlab challenge k8s-valider-et-modifier-a-l-admission
```
