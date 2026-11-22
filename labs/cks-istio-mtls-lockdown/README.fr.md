# Imposer le mTLS entre les Pods d'un maillage Istio

La leçon montre comment fonctionne le mTLS entre Pods, et comment Istio
l'impose par une PeerAuthentication en mode STRICT. Ce cours ajoute ce qu'il
faut vérifier avant d'exiger quoi que ce soit : qu'un Pod porte vraiment son
sidecar, l'identité inscrite dans son certificat, et le mode mTLS qu'Istio lui
applique réellement.

Vous travaillez dans le namespace `essai-mtls`, avec un Pod `serveur`. Le
challenge porte sur d'autres namespaces et d'autres Pods : vous le ferez seul,
à la fin.

Page associée : [mTLS entre les Pods](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/mtls-pod-to-pod/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-istio-mtls-lockdown
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Istio est installé dans le cluster, et `istioctl`
sur le nœud.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
22 novembre 2026, avec Istio 1.31.0.

## 💉 Exercice 1 : l'injection se décide à la création du Pod

Istio ajoute son sidecar aux Pods d'un namespace qui porte le label
`istio-injection=enabled`. Créez un namespace sans ce label, lancez-y un
serveur HTTP, puis posez le label :

```bash
kubectl create namespace essai-mtls; kubectl run serveur -n essai-mtls --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --port=8080 -- httpd -f -p 8080; kubectl wait --for=condition=Ready pod/serveur -n essai-mtls --timeout=120s; kubectl label namespace essai-mtls istio-injection=enabled; kubectl get pod serveur -n essai-mtls
```

```text
namespace/essai-mtls created
pod/serveur created
pod/serveur condition met
namespace/essai-mtls labeled
NAME      READY   STATUS    RESTARTS   AGE
serveur   1/1     Running   0          1s
```

Le Pod reste à `1/1` : un seul conteneur, pas de sidecar. L'injection est
faite par un webhook d'admission, au moment où le Pod est **créé**. Un label
posé après coup ne touche pas aux Pods qui tournent déjà. Recréez le Pod :

```bash
kubectl delete pod serveur -n essai-mtls --wait=true; kubectl run serveur -n essai-mtls --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --port=8080 -- httpd -f -p 8080; kubectl wait --for=condition=Ready pod/serveur -n essai-mtls --timeout=180s; kubectl get pod serveur -n essai-mtls; kubectl get pod serveur -n essai-mtls -o jsonpath='{range .spec.initContainers[*]}{.name}{" restartPolicy="}{.restartPolicy}{"\n"}{end}'
```

```text
pod "serveur" deleted from essai-mtls namespace
pod/serveur created
pod/serveur condition met
NAME      READY   STATUS    RESTARTS   AGE
serveur   2/2     Running   0          2s
istio-init restartPolicy=
istio-proxy restartPolicy=Always
```

`2/2` cette fois. Le sidecar `istio-proxy` est un init container avec
`restartPolicy: Always`, la forme des sidecars natifs de Kubernetes : il
démarre avant l'application et vit aussi longtemps qu'elle. `istio-init`
prépare la redirection du trafic, puis s'arrête. Dans un namespace qu'on
ouvre au maillage, ce sont donc les Pods existants qu'il faut redémarrer,
faute de quoi ils restent hors du maillage sans que rien ne le signale.

## 🪪 Exercice 2 : l'identité du Pod, et le mode mTLS appliqué

Le sidecar reçoit d'Istio un certificat, qui prouve l'identité du Pod aux
autres. Lisez-le dans la configuration du proxy :

```bash
istioctl proxy-config secret serveur -n essai-mtls -o json | jq -r '.dynamicActiveSecrets[] | select(.name=="default") | .secret.tlsCertificate.certificateChain.inlineBytes' | base64 -d | openssl x509 -noout -subject -ext subjectAltName -enddate
```

```text
subject=
X509v3 Subject Alternative Name: critical
    URI:spiffe://cluster.local/ns/essai-mtls/sa/default
notAfter=Nov 23 10:43:24 2026 GMT
```

L'identité est une URI SPIFFE : `spiffe://cluster.local/ns/essai-mtls/sa/default`.
Elle vient du namespace et du compte de service du Pod, pas de son nom ni de
son adresse IP. Le certificat expire le lendemain : Istio le renouvelle
lui-même, bien avant. C'est cette identité qu'une AuthorizationPolicy cite
pour autoriser ou refuser un appelant.

Demandez enfin à `istioctl` le mode mTLS qu'Istio applique à ce Pod :

```bash
istioctl x describe pod serveur -n essai-mtls 2>&1 | grep -iE 'pod:|mtls|peerauthentication|strict|permissive' | head -6
```

```text
Pod: serveur
Effective PeerAuthentication:
   Workload mTLS mode: PERMISSIVE
```

`PERMISSIVE` : le Pod accepte le trafic chiffré **et** le trafic en clair.
C'est le mode par défaut d'Istio, qui permet de migrer sans couper. Tant
qu'aucune PeerAuthentication ne dit autre chose, un client hors du maillage
joint donc ce Pod en clair.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-mtls --wait=true --timeout=120s
```

```text
namespace "essai-mtls" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-istio-mtls-lockdown
dsoxlab check cks-istio-mtls-lockdown
```

```text
╭─ Résultat : cks-istio-mtls-lockdown ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests     │
╰──────────────────────────────────────╯
```

C'est le résultat attendu sur un lab neuf. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un maillage où le chiffrement est possible mais pas
exigé, à fermer aux clients sans certificat sans couper l'application.

```bash
dsoxlab run cks-istio-mtls-lockdown
dsoxlab challenge cks-istio-mtls-lockdown
```
