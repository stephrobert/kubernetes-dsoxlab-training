# Donner un accès humain par une CertificateSigningRequest

La leçon montre comment donner un accès à une personne : elle fabrique une
clé et une demande de certificat, le cluster la signe par une
CertificateSigningRequest (CSR), et RBAC donne les droits. Ce cours ajoute des
cas que la leçon ne montre pas : une demande refusée, une demande adressée au
mauvais signataire, un certificat à durée de vie courte, et un groupe porté
par le champ O du certificat.

Vous travaillez dans un répertoire d'essai, `~/essai-csr`, avec des demandes
`essai-*` et un namespace `essai-csr`. Le challenge porte sur une autre
personne et un autre namespace : vous le ferez seul, à la fin.

Page associée : [La PKI d'un cluster Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/pki-cluster-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-donner-un-acces-par-csr
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà, avec les droits
d'administrateur.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Chaque demande suit le même modèle : `openssl req` fabrique une clé et une
demande, encodée en base64, que la commande place dans une CSR.

## ⛔ Exercice 1 : une demande refusée

Créez une demande pour le signataire des clients de l'API server, puis
refusez-la :

```bash
mkdir -p ~/essai-csr; openssl req -new -newkey rsa:2048 -nodes -keyout ~/essai-csr/essai-refus.key -subj '/CN=essai-refus' 2>/dev/null | base64 -w0 > ~/essai-csr/essai-refus.b64; cat <<YAML | kubectl apply -f -
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: essai-refus
spec:
  request: $(cat ~/essai-csr/essai-refus.b64)
  signerName: kubernetes.io/kube-apiserver-client
  usages: [client auth]
  
YAML
kubectl certificate deny essai-refus; kubectl get csr essai-refus; kubectl get csr essai-refus -o jsonpath='certificat délivré : [{.status.certificate}]{"\n"}'
```

```text
certificatesigningrequest.certificates.k8s.io/essai-refus created
certificatesigningrequest.certificates.k8s.io/essai-refus denied
NAME          AGE   SIGNERNAME                            REQUESTOR          REQUESTEDDURATION   CONDITION
essai-refus   1s    kubernetes.io/kube-apiserver-client   kubernetes-admin   <none>              Denied
certificat délivré : []
```

La demande est `Denied`, et le champ du certificat est vide : rien n'a été
signé. Un refus est définitif. Pour revenir dessus, il faut une nouvelle
demande.

## ✍️ Exercice 2 : un mauvais signataire

Créez une demande adressée à `kubernetes.io/kubelet-serving`, le signataire
des certificats de serveur des kubelets, pour un simple client :

```bash
openssl req -new -newkey rsa:2048 -nodes -keyout ~/essai-csr/essai-mauvais-signataire.key -subj '/CN=essai-mauvais' 2>/dev/null | base64 -w0 > ~/essai-csr/essai-mauvais-signataire.b64; cat <<YAML | kubectl apply -f -
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: essai-mauvais-signataire
spec:
  request: $(cat ~/essai-csr/essai-mauvais-signataire.b64)
  signerName: kubernetes.io/kubelet-serving
  usages: [client auth]
  
YAML
```

```text
certificatesigningrequest.certificates.k8s.io/essai-mauvais-signataire created
```

Approuvez-la, attendez, et lisez son état :

```bash
kubectl certificate approve essai-mauvais-signataire 2>&1; sleep 5; kubectl get csr essai-mauvais-signataire; kubectl get csr essai-mauvais-signataire -o jsonpath='{range .status.conditions[*]}{.type}: {.message}{"\n"}{end}'
```

```text
certificatesigningrequest.certificates.k8s.io/essai-mauvais-signataire approved
NAME                       AGE   SIGNERNAME                      REQUESTOR          REQUESTEDDURATION   CONDITION
essai-mauvais-signataire   5s    kubernetes.io/kubelet-serving   kubernetes-admin   <none>              Approved,Failed
Approved: This CSR was approved by kubectl certificate approve.
Failed: subject organization is not system:nodes
```

`Approved,Failed` : vous avez approuvé, mais le signataire a refusé de signer.
Ce signataire n'émet que pour des nœuds (organisation `system:nodes`).
Approuver ne suffit pas : le signataire vérifie lui aussi ce qu'on lui
demande. Pour un humain, le signataire est `kubernetes.io/kube-apiserver-client`.

## ⏳ Exercice 3 : un certificat qui ne vit que dix minutes

Créez une demande avec `expirationSeconds: 600` et une organisation
`essai-lecteurs`, approuvez-la, puis lisez le sujet et les dates du
certificat délivré :

```bash
openssl req -new -newkey rsa:2048 -nodes -keyout ~/essai-csr/essai-dominique.key -subj '/CN=essai-dominique/O=essai-lecteurs' 2>/dev/null | base64 -w0 > ~/essai-csr/essai-dominique.b64; cat <<YAML | kubectl apply -f -
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: essai-dominique
spec:
  request: $(cat ~/essai-csr/essai-dominique.b64)
  signerName: kubernetes.io/kube-apiserver-client
  usages: [client auth]
  expirationSeconds: 600
YAML
kubectl certificate approve essai-dominique; sleep 3; kubectl get csr essai-dominique -o jsonpath='{.status.certificate}' | base64 -d > ~/essai-csr/essai-dominique.crt; openssl x509 -in ~/essai-csr/essai-dominique.crt -noout -subject -dates
```

```text
certificatesigningrequest.certificates.k8s.io/essai-dominique created
certificatesigningrequest.certificates.k8s.io/essai-dominique approved
subject=O = essai-lecteurs, CN = essai-dominique
notBefore=Nov 21 04:15:50 2026 GMT
notAfter=Nov 21 04:30:50 2026 GMT
```

Le certificat porte le CN et l'organisation demandés. Son début
(`notBefore`) est reculé de quelques minutes, pour tolérer une horloge un peu
en avance : l'écart affiché fait donc plus de dix minutes, mais le certificat
expire bien dix minutes après sa délivrance. Un accès temporaire s'accorde
ainsi, sans avoir à le révoquer ensuite : Kubernetes ne sait pas révoquer un
certificat.

## 👥 Exercice 4 : le groupe porté par le champ O

Fabriquez un kubeconfig avec ce certificat et sa clé, puis demandez à l'API
qui vous êtes :

```bash
SERVEUR=$(kubectl config view --raw -o jsonpath='{.clusters[0].cluster.server}'); kubectl config view --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' | base64 -d > ~/essai-csr/ca.crt; K=~/essai-csr/dominique.kubeconfig; kubectl config set-cluster essai --server=$SERVEUR --certificate-authority=$HOME/essai-csr/ca.crt --embed-certs --kubeconfig=$K >/dev/null; kubectl config set-credentials essai-dominique --client-certificate=$HOME/essai-csr/essai-dominique.crt --client-key=$HOME/essai-csr/essai-dominique.key --embed-certs --kubeconfig=$K >/dev/null; kubectl config set-context essai --cluster=essai --user=essai-dominique --kubeconfig=$K >/dev/null; kubectl config use-context essai --kubeconfig=$K >/dev/null; kubectl auth whoami --kubeconfig=$K
```

```text
ATTRIBUTE                                           VALUE
Username                                            essai-dominique
Groups                                              [essai-lecteurs system:authenticated]
Extra: authentication.kubernetes.io/credential-id   [X509SHA256=116ccd97ee7343173c3244d62fab5daf086c380c8ceb9a6e14ab2eae77467972]
```

Le CN devient le nom d'utilisateur, et l'organisation (champ O) devient un
groupe : `essai-lecteurs`. Donnez des droits à ce groupe dans un namespace
d'essai, et essayez de lire les Pods, dans ce namespace puis dans `default` :

```bash
kubectl create namespace essai-csr; kubectl create rolebinding lecteurs-du-groupe -n essai-csr --clusterrole=view --group=essai-lecteurs; kubectl get pods -n essai-csr --kubeconfig=$HOME/essai-csr/dominique.kubeconfig; kubectl get pods -n default --kubeconfig=$HOME/essai-csr/dominique.kubeconfig 2>&1 | cut -c1-140
```

```text
namespace/essai-csr created
rolebinding.rbac.authorization.k8s.io/lecteurs-du-groupe created
No resources found in essai-csr namespace.
Error from server (Forbidden): pods is forbidden: User "essai-dominique" cannot list resource "pods" in API group "" in the namespace "defau
```

La lecture passe dans `essai-csr` (aucun Pod, mais pas d'erreur), et elle est
refusée dans `default`. Le droit vient du groupe écrit dans le certificat :
tout certificat signé avec `O=essai-lecteurs` reçoit ces droits. Choisir le
champ O d'une demande revient donc à choisir des droits, ce qui se vérifie
avant d'approuver.

## 🧹 Nettoyage

Supprimez les trois demandes, le namespace et le répertoire d'essai :

```bash
kubectl delete csr essai-refus essai-mauvais-signataire essai-dominique; kubectl delete namespace essai-csr; rm -rf ~/essai-csr
```

```text
certificatesigningrequest.certificates.k8s.io "essai-refus" deleted
certificatesigningrequest.certificates.k8s.io "essai-mauvais-signataire" deleted
certificatesigningrequest.certificates.k8s.io "essai-dominique" deleted
namespace "essai-csr" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-donner-un-acces-par-csr
dsoxlab check k8s-donner-un-acces-par-csr
```

```text
╭─ Résultat : k8s-donner-un-acces-par-csr ─╮
│  0 / 100 pts                             │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests         │
╰──────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un accès en lecture aux Pods d'un namespace pour
une nouvelle personne, par une demande de certificat, et rien de plus.

```bash
dsoxlab run k8s-donner-un-acces-par-csr
dsoxlab challenge k8s-donner-un-acces-par-csr
```
