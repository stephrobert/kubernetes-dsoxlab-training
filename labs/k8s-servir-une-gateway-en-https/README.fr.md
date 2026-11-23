# Servir une Gateway en HTTPS

La leçon demande un certificat à cert-manager, déclare une Gateway d'Istio
avec un listener HTTPS qui s'en sert, y attache une route, puis lit le
certificat que présente le listener. C'est le challenge du lab : ce cours ne
crée aucune Gateway. Il travaille le certificat lui-même, ce que la leçon ne
montre pas : un certificat qui ne sort pas, ce que contient un certificat
émis, le nom que vérifie le client, la confiance limitée à la CA interne, et
le renouvellement quand le Secret disparaît.

Vous travaillez dans le namespace `essai-tls`, pour le nom
`essai.formation.test`, et dans un répertoire d'essai, `~/essai-tls`. Le
challenge porte sur un autre nom, un autre namespace et la Gateway : vous le
ferez seul, à la fin.

Page associée : [Servir une Gateway en HTTPS avec cert-manager](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/reseau-avance/tls-gateway-api/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-servir-une-gateway-en-https
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le control plane du cluster
kubeadm. cert-manager y tourne, avec deux émetteurs à l'échelle du cluster :
`amorce-auto-signee`, qui a servi à créer la CA, et `ca-formation`, la CA
interne. Créez le namespace d'essai :

```bash
kubectl get clusterissuer
kubectl create namespace essai-tls
```

```text
NAME                 READY   AGE
amorce-auto-signee   True    3s
ca-formation         True    3s
namespace/essai-tls created
```

Les sorties montrées dans ce cours ont été relevées sur cette machine le
22 novembre 2026 (Kubernetes v1.37.2, cert-manager v1.21.3).

## 🚫 Exercice 1 : un certificat qui ne sort pas

Demandez un certificat à un émetteur qui n'existe pas, `ca-absente`, comme
après une faute de frappe :

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: essai-orphelin
  namespace: essai-tls
spec:
  secretName: essai-orphelin-tls
  dnsNames:
    - orphelin.formation.test
  issuerRef:
    kind: ClusterIssuer
    name: ca-absente
YAML
sleep 10
kubectl -n essai-tls get certificate essai-orphelin
kubectl -n essai-tls get certificaterequest -o jsonpath='{range .items[*]}{.metadata.name}: {range .status.conditions[*]}{.type}={.status} {.reason}: {.message}{"\n"}{end}{end}'
kubectl -n essai-tls delete certificate essai-orphelin
```

```text
certificate.cert-manager.io/essai-orphelin created
NAME             READY   SECRET               AGE
essai-orphelin   False   essai-orphelin-tls   10s
essai-orphelin-1: Approved=True cert-manager.io: Certificate request has been approved by cert-manager.io
Ready=False Pending: Referenced "ClusterIssuer" not found: clusterissuer.cert-manager.io "ca-absente" not found
certificate.cert-manager.io "essai-orphelin" deleted from essai-tls namespace
```

Le Certificate reste `READY False`, sans dire pourquoi. La cause est un
niveau plus bas : cert-manager crée une **CertificateRequest**,
`essai-orphelin-1`, et c'est elle qui porte le message, `Referenced
"ClusterIssuer" not found`, avec le nom fautif. Une Gateway qui attend ce
Secret n'aurait jamais de certificat à présenter.

## 📜 Exercice 2 : ce que contient un certificat émis

Demandez maintenant un certificat valable deux heures à la CA interne, et
lisez-le. Le Secret de cert-manager range le certificat (`tls.crt`) et la CA
qui l'a émis (`ca.crt`) :

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: essai
  namespace: essai-tls
spec:
  secretName: essai-tls
  duration: 2h
  renewBefore: 1h
  dnsNames:
    - essai.formation.test
  issuerRef:
    kind: ClusterIssuer
    name: ca-formation
YAML
kubectl -n essai-tls wait --for=condition=Ready certificate/essai --timeout=60s
mkdir -p ~/essai-tls && cd ~/essai-tls
kubectl -n essai-tls get secret essai-tls -o jsonpath='{.data.tls\.crt}' | base64 -d > essai.crt
kubectl -n essai-tls get secret essai-tls -o jsonpath='{.data.ca\.crt}' | base64 -d > ca.crt
openssl x509 -in essai.crt -noout -subject -issuer -ext subjectAltName -startdate -enddate
```

```text
certificate.cert-manager.io/essai created
certificate.cert-manager.io/essai condition met
subject=
issuer=O = Formation Kubernetes, CN = CA de la formation
X509v3 Subject Alternative Name: critical
    DNS:essai.formation.test
notBefore=Nov 22 23:17:39 2026 GMT
notAfter=Nov 23 01:17:39 2026 GMT
```

Le sujet est **vide** : cert-manager met le nom dans l'extension *Subject
Alternative Name* (SAN), marquée `critical`, et c'est là que les clients
modernes le cherchent. L'émetteur est la CA de la formation, et la validité
dure exactement les deux heures de `duration`. Avec `renewBefore: 1h`,
cert-manager renouvellera le certificat une heure avant son expiration.

## 🏷️ Exercice 3 : le nom que vérifie le client

Un client HTTPS ne se contente pas d'une signature valide : il vérifie aussi
que le certificat porte le nom qu'il a demandé. `openssl verify` sait faire
les deux, avec `-verify_hostname`. Vérifiez le certificat pour son nom, puis
pour un autre :

```bash
openssl verify -CAfile ca.crt -verify_hostname essai.formation.test essai.crt
openssl verify -CAfile ca.crt -verify_hostname autre.formation.test essai.crt
echo "code=$?"
```

```text
essai.crt: OK

error 62 at 0 depth lookup: hostname mismatch
error essai.crt: verification failed
code=2
```

Même certificat, même CA, mais le second nom échoue en `hostname mismatch`.
C'est l'erreur que verrait un navigateur venu par un nom que le listener
n'a pas dans son certificat : la signature est bonne, le nom ne l'est pas.

## 🔐 Exercice 4 : la confiance limitée à la CA interne

Sans `-CAfile`, `openssl` ne fait confiance qu'aux autorités publiques
installées sur la machine :

```bash
openssl verify essai.crt
echo "code=$?"
```

```text

error 20 at 0 depth lookup: unable to get local issuer certificate
error essai.crt: verification failed
code=2
```

`unable to get local issuer certificate` : aucune autorité connue de la
machine n'a signé ce certificat. C'est le comportement voulu d'une CA
interne. Un client ne fera confiance au listener que si on lui donne la CA de
la formation, comme le fait le contrôle du challenge.

## 🔄 Exercice 5 : le renouvellement quand le Secret disparaît

cert-manager surveille le Secret de chaque Certificate. Relevez le numéro de
série du certificat et la révision du Certificate, supprimez le Secret, puis
relisez les deux :

```bash
openssl x509 -in essai.crt -noout -serial
kubectl -n essai-tls get certificate essai -o jsonpath='revision={.status.revision}{"\n"}'
kubectl -n essai-tls delete secret essai-tls
sleep 10
kubectl -n essai-tls get certificate essai -o jsonpath='revision={.status.revision}{"\n"}'
kubectl -n essai-tls get secret essai-tls -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -serial
```

```text
serial=3F3E8F2AB4FF19E8AE22B565C60B329B2D28BD68
revision=1
secret "essai-tls" deleted from essai-tls namespace
revision=2
serial=381729420D73547BCBE37EA8450E6512B5E76834
```

En moins de dix secondes, cert-manager a recréé le Secret avec un
**nouveau** certificat : la révision passe à 2 et le numéro de série change.
Le Secret garde son nom : ce qui le référence, comme un listener, n'a rien à
modifier. Le fichier `essai.crt` du répertoire d'essai, lui, est resté
l'ancien : une copie prise à la main ne suit pas les renouvellements.

## 🧹 Nettoyage

Supprimez le répertoire d'essai et le namespace, qui emporte le Certificate
et son Secret :

```bash
cd ~ && rm -rf ~/essai-tls
kubectl delete namespace essai-tls --wait=true --timeout=120s
```

```text
namespace "essai-tls" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-servir-une-gateway-en-https
dsoxlab check k8s-servir-une-gateway-en-https
```

```text
╭─ Résultat : k8s-servir-une-gateway-en-https ─╮
│  0 / 100 pts                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests             │
╰──────────────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : demander le certificat d'une application, le
confier au listener HTTPS d'une Gateway d'Istio, et prouver qu'un client qui
ne fait confiance qu'à la CA interne l'atteint.

```bash
dsoxlab run k8s-servir-une-gateway-en-https
dsoxlab challenge k8s-servir-une-gateway-en-https
```
