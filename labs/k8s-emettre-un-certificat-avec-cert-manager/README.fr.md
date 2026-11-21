# Émettre des certificats avec cert-manager et une CA interne

La leçon montre cert-manager : des Issuers qui signent, et des Certificates
qui décrivent les certificats voulus et les tiennent à jour. Ce cours ajoute
des cas que la leçon ne montre pas : la durée de vie et le moment du
renouvellement, un Secret supprimé que cert-manager réémet, la clé privée
remplacée ou gardée quand la demande change, et un Issuer qui ne sert que son
namespace.

Vous travaillez dans deux namespaces d'essai, `essai-cm` et `essai-ailleurs`,
avec un Issuer auto-signé `essai-racine` et un Certificate `guichet-tls`. Le
challenge porte sur un autre namespace : vous le ferez seul, à la fin.

Page associée : [cert-manager](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cert-manager/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-emettre-un-certificat-avec-cert-manager
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà. Le lab a installé
cert-manager.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2 et cert-manager v1.21.3.

Créez le namespace et un Issuer auto-signé, qui signe chaque certificat avec
sa propre clé :

```bash
kubectl create namespace essai-cm; cat <<'YAML' | kubectl apply -n essai-cm -f -
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: essai-racine
spec:
  selfSigned: {}
YAML
kubectl wait --for=condition=Ready issuer/essai-racine -n essai-cm --timeout=60s
```

```text
namespace/essai-cm created
issuer.cert-manager.io/essai-racine created
issuer.cert-manager.io/essai-racine condition met
```

## ⏳ Exercice 1 : durée de vie et moment du renouvellement

Demandez un certificat valable 2 heures (`duration`), à renouveler 90 minutes
avant son échéance (`renewBefore`), puis lisez ses dates :

```bash
cat <<'YAML' | kubectl apply -n essai-cm -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: guichet-tls
spec:
  secretName: guichet-tls
  dnsNames: [guichet.essai-cm.svc]
  duration: 2h
  renewBefore: 90m
  issuerRef: {name: essai-racine, kind: Issuer}
YAML
kubectl wait --for=condition=Ready certificate/guichet-tls -n essai-cm --timeout=60s; kubectl get certificate guichet-tls -n essai-cm -o jsonpath='pas avant={.status.notBefore} échéance={.status.notAfter} renouvellement={.status.renewalTime}{"\n"}'
```

```text
certificate.cert-manager.io/guichet-tls created
certificate.cert-manager.io/guichet-tls condition met
pas avant=2026-11-21T05:13:50Z échéance=2026-11-21T07:13:50Z renouvellement=2026-11-21T05:43:50Z
```

Échéance 2 heures après l'émission, et renouvellement prévu 30 minutes après
l'émission : 2 heures moins 90 minutes. cert-manager renouvellera seul à
cette date, sans rien attendre de vous. Un `renewBefore` trop proche de
`duration` fait renouveler sans cesse, un `renewBefore` trop court laisse peu
de marge si l'émission échoue.

## ♻️ Exercice 2 : le Secret supprimé revient

Notez l'empreinte de la clé publique du certificat, supprimez son Secret,
attendez 10 secondes, et regardez :

```bash
kubectl get secret guichet-tls -n essai-cm -o jsonpath='{.data.tls\.key}' | base64 -d | openssl pkey -pubout 2>/dev/null | sha256sum | cut -c1-16; kubectl delete secret guichet-tls -n essai-cm; sleep 10; kubectl get secret guichet-tls -n essai-cm; kubectl get secret guichet-tls -n essai-cm -o jsonpath='{.data.tls\.key}' | base64 -d | openssl pkey -pubout 2>/dev/null | sha256sum | cut -c1-16
```

```text
fd497c14300f5ad9
secret "guichet-tls" deleted from essai-cm namespace
NAME          TYPE                DATA   AGE
guichet-tls   kubernetes.io/tls   3      10s
11f8274fa58427fa
```

Le Secret est revenu, avec une autre clé. cert-manager surveille le Secret
décrit par le Certificate, et le recrée dès qu'il manque. Chaque émission
passe par une CertificateRequest :

```bash
kubectl get certificaterequests -n essai-cm -o custom-columns=NOM:.metadata.name,PRET:.status.conditions[0].status
```

```text
NOM             PRET
guichet-tls-2   True
```

`guichet-tls-2` : c'est la deuxième demande de ce Certificate. Supprimer le
Secret est donc un moyen de forcer une réémission.

## 🔑 Exercice 3 : changer la demande, garder ou changer la clé

Lisez la politique de rotation de la clé, puis ajoutez un nom au certificat,
et comparez les empreintes avant et après :

```bash
kubectl get certificate guichet-tls -n essai-cm -o jsonpath='rotationPolicy={.spec.privateKey.rotationPolicy}{"\n"}'; kubectl get secret guichet-tls -n essai-cm -o jsonpath='{.data.tls\.key}' | base64 -d | openssl pkey -pubout 2>/dev/null | sha256sum | cut -c1-16; kubectl patch certificate guichet-tls -n essai-cm --type merge -p '{"spec":{"dnsNames":["guichet.essai-cm.svc","guichet"]}}'; sleep 10; kubectl get secret guichet-tls -n essai-cm -o jsonpath='{.data.tls\.key}' | base64 -d | openssl pkey -pubout 2>/dev/null | sha256sum | cut -c1-16
```

```text
rotationPolicy=
11f8274fa58427fa
certificate.cert-manager.io/guichet-tls patched
d21b32401ea48a0b
```

La politique est vide, donc celle par défaut, et la clé a changé : à chaque
réémission, cert-manager fabrique une nouvelle clé. Passez la politique à
`Never`, puis changez encore les noms, deux fois :

```bash
kubectl patch certificate guichet-tls -n essai-cm --type merge -p '{"spec":{"privateKey":{"rotationPolicy":"Never"},"dnsNames":["guichet.essai-cm.svc"]}}'; sleep 10; kubectl get secret guichet-tls -n essai-cm -o jsonpath='{.data.tls\.key}' | base64 -d | openssl pkey -pubout 2>/dev/null | sha256sum | cut -c1-16; kubectl patch certificate guichet-tls -n essai-cm --type merge -p '{"spec":{"dnsNames":["guichet.essai-cm.svc","guichet"]}}'; sleep 10; kubectl get secret guichet-tls -n essai-cm -o jsonpath='{.data.tls\.key}' | base64 -d | openssl pkey -pubout 2>/dev/null | sha256sum | cut -c1-16
```

```text
certificate.cert-manager.io/guichet-tls patched
d21b32401ea48a0b
certificate.cert-manager.io/guichet-tls patched
d21b32401ea48a0b
```

La clé ne bouge plus. Avec `rotationPolicy: Never`, cert-manager garde la clé
existante et ne change que le certificat. C'est utile quand la clé est
épinglée ailleurs, au prix d'une clé qui ne tourne jamais.

## 🚪 Exercice 4 : un Issuer ne sert que son namespace

Dans un autre namespace, demandez un certificat à `essai-racine` :

```bash
kubectl create namespace essai-ailleurs; cat <<'YAML' | kubectl apply -n essai-ailleurs -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: voisin-tls
spec:
  secretName: voisin-tls
  dnsNames: [voisin.essai-ailleurs.svc]
  issuerRef: {name: essai-racine, kind: Issuer}
YAML
sleep 10; kubectl get certificate voisin-tls -n essai-ailleurs; kubectl get certificaterequests -n essai-ailleurs -o jsonpath='{range .items[*].status.conditions[*]}{.type}={.status} {.reason}: {.message}{"\n"}{end}'
```

```text
namespace/essai-ailleurs created
certificate.cert-manager.io/voisin-tls created
NAME         READY   SECRET       AGE
voisin-tls   False   voisin-tls   10s
Approved=True cert-manager.io: Certificate request has been approved by cert-manager.io
Ready=False Pending: Referenced "Issuer" not found: issuer.cert-manager.io "essai-racine" not found
```

La demande est approuvée, mais reste en attente : `essai-racine` n'existe pas
dans ce namespace. Un `Issuer` ne signe que pour son propre namespace. Pour un
émetteur commun à tout le cluster, il faut un `ClusterIssuer`.

## 🧹 Nettoyage

Supprimez les deux namespaces d'essai :

```bash
kubectl delete namespace essai-cm essai-ailleurs
```

```text
namespace "essai-cm" deleted
namespace "essai-ailleurs" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-emettre-un-certificat-avec-cert-manager
dsoxlab check k8s-emettre-un-certificat-avec-cert-manager
```

```text
╭─ Résultat : k8s-emettre-un-certificat-avec-cert-manager ─╮
│  0 / 100 pts                                             │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                         │
╰──────────────────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une CA interne à monter avec cert-manager, des
certificats à émettre, et un certificat en panne à réparer.

```bash
dsoxlab run k8s-emettre-un-certificat-avec-cert-manager
dsoxlab challenge k8s-emettre-un-certificat-avec-cert-manager
```
