# Imposer des règles avec Gatekeeper

La leçon présente Gatekeeper : son installation, le couple ConstraintTemplate
et Constraint, les trois modes `dryrun`, `warn` et `deny`, l'audit des
ressources existantes et les tests locaux avec gator. Ce cours vous fait faire
chacun de ces gestes sur le cluster, avec deux règles d'essai : pas de volume
`hostPath`, pas de conteneur `privileged`.

Vous travaillez dans le namespace `essai-gk` et le répertoire
`~/essai-gator`. Le challenge porte sur une autre règle et un autre
namespace : vous le ferez seul, à la fin.

Page associée : [OPA Gatekeeper](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/gatekeeper/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-imposer-des-regles-avec-gatekeeper
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
23 novembre 2026, avec Kubernetes v1.37.2 et Gatekeeper v3.23.1.

## 📦 Exercice 1 : installer Gatekeeper

Installez Gatekeeper depuis le manifeste de sa release, épinglé par son tag,
puis attendez ses deux Deployments :

```bash
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/v3.23.1/deploy/gatekeeper.yaml | tail -2
kubectl -n gatekeeper-system rollout status deployment gatekeeper-controller-manager --timeout=300s
kubectl -n gatekeeper-system rollout status deployment gatekeeper-audit --timeout=300s
kubectl -n gatekeeper-system get pods
kubectl get validatingwebhookconfiguration gatekeeper-validating-webhook-configuration -o jsonpath='{range .webhooks[*]}{.name} {.failurePolicy}{"\n"}{end}'
```

```text
mutatingwebhookconfiguration.admissionregistration.k8s.io/gatekeeper-mutating-webhook-configuration created
validatingwebhookconfiguration.admissionregistration.k8s.io/gatekeeper-validating-webhook-configuration created
Waiting for deployment "gatekeeper-controller-manager" rollout to finish: 0 of 3 updated replicas are available...
Waiting for deployment "gatekeeper-controller-manager" rollout to finish: 1 of 3 updated replicas are available...
Waiting for deployment "gatekeeper-controller-manager" rollout to finish: 2 of 3 updated replicas are available...
deployment "gatekeeper-controller-manager" successfully rolled out
deployment "gatekeeper-audit" successfully rolled out
NAME                                             READY   STATUS    RESTARTS      AGE
gatekeeper-audit-75d6fc8fd4-ljr42                1/1     Running   2 (13s ago)   25s
gatekeeper-controller-manager-5f7bd474ff-9jpvh   1/1     Running   0             25s
gatekeeper-controller-manager-5f7bd474ff-kplxm   1/1     Running   0             25s
gatekeeper-controller-manager-5f7bd474ff-kzwgg   1/1     Running   0             25s
validation.gatekeeper.sh Ignore
check-ignore-label.gatekeeper.sh Fail
```

Trois contrôleurs (le webhook d'admission, en haute disponibilité) et un Pod
d'audit tournent après 27 secondes. Le Pod d'audit a redémarré
pendant que le webhook démarrait (une fois ou deux selon les essais), puis il
est resté stable. Le webhook
principal, `validation.gatekeeper.sh`, est en `Ignore` : si Gatekeeper tombe,
les requêtes passent sans contrôle.

## 🔍 Exercice 2 : une règle en dryrun, et ce que l'audit en dit

Créez le namespace d'essai et un Pod qui monte le répertoire `/etc` du nœud
par un volume `hostPath`. Écrivez ensuite un ConstraintTemplate qui interdit
ces volumes, attendez que la CRD qu'il déclare soit prête, puis créez sa
Constraint en mode `dryrun`, limitée à `essai-gk`. Gatekeeper crée cette CRD
quelques instants après le template : la boucle `until` attend qu'elle existe,
puis `kubectl wait` attend qu'elle soit utilisable.

```bash
kubectl create namespace essai-gk
cat > hostpath-pod.yaml <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: essai-hote
spec:
  containers:
    - name: c
      image: busybox:1.37
      command: ["sleep", "3600"]
      volumeMounts:
        - name: etc-hote
          mountPath: /hote
  volumes:
    - name: etc-hote
      hostPath:
        path: /etc
YAML
kubectl -n essai-gk apply -f hostpath-pod.yaml
cat <<'YAML' | kubectl apply -f -
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: essaisanshostpath
spec:
  crd:
    spec:
      names:
        kind: EssaiSansHostPath
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package essaisanshostpath

        violation[{"msg": msg}] {
          volume := input.review.object.spec.volumes[_]
          volume.hostPath
          msg := sprintf("Volume hostPath '%v' interdit", [volume.name])
        }
YAML
until kubectl get crd essaisanshostpath.constraints.gatekeeper.sh >/dev/null 2>&1; do sleep 2; done
kubectl wait --for=condition=established crd/essaisanshostpath.constraints.gatekeeper.sh --timeout=60s
cat <<'YAML' | kubectl apply -f -
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: EssaiSansHostPath
metadata:
  name: essai-sans-hostpath
spec:
  enforcementAction: dryrun
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    namespaces: ["essai-gk"]
YAML
sleep 5; sed 's/essai-hote/essai-hote-2/' hostpath-pod.yaml | kubectl -n essai-gk apply -f -
```

```text
namespace/essai-gk created
pod/essai-hote created
constrainttemplate.templates.gatekeeper.sh/essaisanshostpath created
customresourcedefinition.apiextensions.k8s.io/essaisanshostpath.constraints.gatekeeper.sh condition met
essaisanshostpath.constraints.gatekeeper.sh/essai-sans-hostpath created
pod/essai-hote-2 created
```

Le second Pod, créé après la Constraint, passe quand même : en `dryrun`,
Gatekeeper n'empêche rien. Attendez un passage de l'audit (une fois par
minute), puis lisez le `status` de la Constraint :

```bash
sleep 70
kubectl get essaisanshostpath essai-sans-hostpath -o jsonpath='{range .status.violations[*]}{.enforcementAction} {.namespace}/{.name}: {.message}{"\n"}{end}'
kubectl get constraints
```

```text
dryrun essai-gk/essai-hote-2: Volume hostPath 'etc-hote' interdit
dryrun essai-gk/essai-hote: Volume hostPath 'etc-hote' interdit
NAME                  ENFORCEMENT-ACTION   TOTAL-VIOLATIONS
essai-sans-hostpath   dryrun               2
```

L'audit relève les deux Pods, y compris `essai-hote`, créé **avant** la
règle : l'admission ne l'a jamais vu passer. C'est ce relevé qu'on lit avant
de passer une règle en `deny`, pour savoir ce qu'elle casserait.

## 🚫 Exercice 3 : passer la règle en deny

Changez le mode de la Constraint, sans toucher au template, puis essayez de
créer un troisième Pod avec un volume `hostPath` :

```bash
kubectl patch essaisanshostpath essai-sans-hostpath --type=merge -p '{"spec":{"enforcementAction":"deny"}}'
sleep 5; sed 's/essai-hote/essai-hote-3/' hostpath-pod.yaml | kubectl -n essai-gk apply -f -
kubectl -n essai-gk get pods
```

```text
essaisanshostpath.constraints.gatekeeper.sh/essai-sans-hostpath patched
Error from server (Forbidden): error when creating "STDIN": admission webhook "validation.gatekeeper.sh" denied the request: [essai-sans-hostpath] Volume hostPath 'etc-hote' interdit
NAME           READY   STATUS    RESTARTS   AGE
essai-hote     1/1     Running   0          69s
essai-hote-2   1/1     Running   0          61s
```

Le troisième Pod est refusé, et le message nomme la Constraint entre
crochets. Les deux Pods déjà créés tournent toujours : `deny` agit à
l'admission, il ne supprime rien.

## ⚠️ Exercice 4 : une règle en warn

Créez une seconde règle, qui vise les conteneurs `privileged`, en mode `warn`.
Soumettez ensuite un Pod privilégié avec `--dry-run=server` : la requête passe
par toute l'admission, mais rien n'est enregistré.

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: essaisansprivileged
spec:
  crd:
    spec:
      names:
        kind: EssaiSansPrivileged
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package essaisansprivileged

        violation[{"msg": msg}] {
          c := input.review.object.spec.containers[_]
          c.securityContext.privileged == true
          msg := sprintf("Conteneur '%v' en mode privileged", [c.name])
        }
YAML
until kubectl get crd essaisansprivileged.constraints.gatekeeper.sh >/dev/null 2>&1; do sleep 2; done
kubectl wait --for=condition=established crd/essaisansprivileged.constraints.gatekeeper.sh --timeout=60s
cat <<'YAML' | kubectl apply -f -
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: EssaiSansPrivileged
metadata:
  name: essai-sans-privileged
spec:
  enforcementAction: warn
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    namespaces: ["essai-gk"]
YAML
sleep 5; kubectl -n essai-gk run essai-priv --image=busybox:1.37 --restart=Never --dry-run=server --overrides='{"spec":{"containers":[{"name":"essai-priv","image":"busybox:1.37","command":["sleep","60"],"securityContext":{"privileged":true}}]}}'
```

```text
constrainttemplate.templates.gatekeeper.sh/essaisansprivileged created
customresourcedefinition.apiextensions.k8s.io/essaisansprivileged.constraints.gatekeeper.sh condition met
essaisansprivileged.constraints.gatekeeper.sh/essai-sans-privileged created
Warning: [essai-sans-privileged] Conteneur 'essai-priv' en mode privileged
pod/essai-priv created (server dry run)
```

Le Pod est accepté, avec un avertissement qui porte le même texte qu'un
refus. Le mode `warn` prévient sans bloquer : c'est l'étape où les équipes
découvrent la règle avant qu'elle ne refuse.

## 🧪 Exercice 5 : tester une règle hors du cluster avec gator

gator, la CLI de Gatekeeper, évalue une règle sur des fichiers, sans cluster.
Téléchargez-la, vérifiez sa somme de contrôle, puis écrivez le template, une
Constraint et deux Pods dans un répertoire de travail :

```bash
mkdir -p ~/essai-gator && cd ~/essai-gator
curl -fsSLO https://github.com/open-policy-agent/gatekeeper/releases/download/v3.23.1/gator-v3.23.1-linux-amd64.tar.gz
curl -fsSLO https://github.com/open-policy-agent/gatekeeper/releases/download/v3.23.1/sha256sums.txt
grep gator-v3.23.1-linux-amd64.tar.gz sha256sums.txt | sed 's#\./##' | sha256sum -c -
tar xzf gator-v3.23.1-linux-amd64.tar.gz gator
cat > template.yaml <<'YAML'
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: essaisanshostpath
spec:
  crd:
    spec:
      names:
        kind: EssaiSansHostPath
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package essaisanshostpath

        violation[{"msg": msg}] {
          volume := input.review.object.spec.volumes[_]
          volume.hostPath
          msg := sprintf("Volume hostPath '%v' interdit", [volume.name])
        }
YAML
cat > constraint.yaml <<'YAML'
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: EssaiSansHostPath
metadata:
  name: essai-sans-hostpath
spec:
  enforcementAction: deny
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
YAML
cp ~/hostpath-pod.yaml pod-hostpath.yaml
cat > pod-simple.yaml <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: essai-simple
spec:
  containers:
    - name: c
      image: busybox:1.37
YAML
```

```text
gator-v3.23.1-linux-amd64.tar.gz: OK
```

`gator test` évalue un objet contre le template et sa Constraint. Lancez-le
sur chacun des deux Pods :

```bash
./gator test --filename template.yaml --filename constraint.yaml --filename pod-hostpath.yaml; echo "code=$?"
./gator test --filename template.yaml --filename constraint.yaml --filename pod-simple.yaml; echo "code=$?"
```

```text
v1/Pod essai-hote: ["essai-sans-hostpath"] Message: "Volume hostPath 'etc-hote' interdit"
code=1
code=0
```

Le Pod au volume `hostPath` sort en code 1 avec la violation, le Pod simple en
code 0 sans rien dire. Un pipeline peut s'arrêter sur ce code. `gator verify`
va plus loin : il joue une suite de cas, chacun avec le résultat attendu.

```bash
cat > suite.yaml <<'YAML'
kind: Suite
apiVersion: test.gatekeeper.sh/v1alpha1
tests:
  - name: sans-hostpath
    template: template.yaml
    constraint: constraint.yaml
    cases:
      - name: pod-hostpath-refuse
        object: pod-hostpath.yaml
        assertions:
          - violations: yes
      - name: pod-simple-passe
        object: pod-simple.yaml
        assertions:
          - violations: no
YAML
./gator verify suite.yaml
sed -i 's/violations: no/violations: yes/' suite.yaml
./gator verify suite.yaml
cd ~
```

```text
ok	suite.yaml	0.006s
PASS
    --- FAIL: pod-simple-passe	(0.002s)
        unexpected number of violations: got 0 violations but want at least 1: got messages []
--- FAIL: sans-hostpath	(0.006s)
FAIL	suite.yaml	0.006s
FAIL
Error: FAIL
```

La suite passe. Faussez ensuite une attente (le Pod simple « devrait » être
refusé) : gator nomme le cas qui échoue et dit pourquoi. C'est ce qui fait
d'une suite gator un vrai test, et pas une simple relecture.

## 🧹 Nettoyage

Supprimez les Constraints, puis les templates (leur suppression retire les
CRD qu'ils ont créées), le namespace d'essai, et enfin Gatekeeper lui-même
avec le même manifeste qu'à l'installation. Les dernières commandes comptent
ce qui reste de Gatekeeper :

```bash
kubectl delete essaisanshostpath essai-sans-hostpath
kubectl delete essaisansprivileged essai-sans-privileged
kubectl delete constrainttemplate essaisanshostpath essaisansprivileged
kubectl delete namespace essai-gk --wait=true --timeout=120s
kubectl delete -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/v3.23.1/deploy/gatekeeper.yaml --wait=true | tail -2
rm -rf ~/essai-gator ~/hostpath-pod.yaml
kubectl get crd -o name | grep -c gatekeeper.sh
kubectl get validatingwebhookconfiguration,mutatingwebhookconfiguration -o name | grep -c gatekeeper
```

```text
essaisanshostpath.constraints.gatekeeper.sh "essai-sans-hostpath" deleted
essaisansprivileged.constraints.gatekeeper.sh "essai-sans-privileged" deleted
constrainttemplate.templates.gatekeeper.sh "essaisanshostpath" deleted
constrainttemplate.templates.gatekeeper.sh "essaisansprivileged" deleted
namespace "essai-gk" deleted
mutatingwebhookconfiguration.admissionregistration.k8s.io "gatekeeper-mutating-webhook-configuration" deleted
validatingwebhookconfiguration.admissionregistration.k8s.io "gatekeeper-validating-webhook-configuration" deleted
0
0
```

Plus aucune CRD ni aucun webhook de Gatekeeper. Quittez ensuite la machine et
remettez le lab à zéro. `dsoxlab reset` rejoue le nettoyage puis la
préparation du lab : vous retrouvez exactement l'état de départ du challenge.
Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-imposer-des-regles-avec-gatekeeper
dsoxlab check k8s-imposer-des-regles-avec-gatekeeper
```

```text
╭─ Résultat : k8s-imposer-des-regles-avec-gatekeeper ─╮
│  0 / 100 pts                                        │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests                    │
╰─────────────────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : installer Gatekeeper, lui faire refuser dans un
namespace les images qui ne viennent pas du registre autorisé, et lire dans
son audit le Pod qui tournait avant la règle.

```bash
dsoxlab run k8s-imposer-des-regles-avec-gatekeeper
dsoxlab challenge k8s-imposer-des-regles-avec-gatekeeper
```
