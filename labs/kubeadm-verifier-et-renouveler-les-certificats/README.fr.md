# Vérifier et renouveler les certificats d'un cluster kubeadm

La leçon montre la PKI d'un cluster kubeadm : les certificats du plan de
contrôle, leur échéance, et `kubeadm certs renew`. Ce cours ajoute des cas
que la leçon ne montre pas : les noms que couvre le certificat de l'API
server, le certificat client du kubelet qui se renouvelle tout seul, et un
renouvellement fait sur une copie de la PKI, pour voir ce qui change dans le
certificat.

Le cours ne renouvelle rien dans `/etc/kubernetes/pki` : il travaille sur une
copie, `/tmp/essai-pki`. Le challenge porte sur les vrais certificats : vous
le ferez seul, à la fin.

Page associée : [La PKI d'un cluster Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/pki-cluster-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run kubeadm-verifier-et-renouveler-les-certificats
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà. Les certificats sont
lisibles par root seulement : les commandes utilisent `sudo`.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

## 🏷️ Exercice 1 : les noms que couvre l'API server

Lisez les noms et les adresses du certificat de l'API server :

```bash
sudo openssl x509 -in /etc/kubernetes/pki/apiserver.crt -noout -ext subjectAltName
```

```text
X509v3 Subject Alternative Name: 
    DNS:k8s-cp.lab, DNS:kubernetes, DNS:kubernetes.default, DNS:kubernetes.default.svc, DNS:kubernetes.default.svc.cluster.local, IP Address:10.96.0.1, IP Address:10.10.50.11
```

Le nom du nœud, les noms internes de Kubernetes, l'adresse du Service
`kubernetes` (`10.96.0.1`) et celle du nœud. Un client qui joint l'API par un
autre nom, une autre adresse ou un répartiteur ajouté plus tard est refusé.
C'est la première chose à lire quand `kubectl` se plaint d'un certificat qui
ne correspond pas.

## 🔁 Exercice 2 : le kubelet renouvelle son certificat client lui-même

Regardez les certificats du kubelet, et le sujet de son certificat client :

```bash
sudo ls -l /var/lib/kubelet/pki/ | cut -c1-140; sudo openssl x509 -in /var/lib/kubelet/pki/kubelet-client-current.pem -noout -subject -enddate
```

```text
total 12
-rw------- 1 root root 2830 Nov 21 03:53 kubelet-client-2026-11-21-03-53-43.pem
lrwxrwxrwx 1 root root   59 Nov 21 03:53 kubelet-client-current.pem -> /var/lib/kubelet/pki/kubelet-client-2026-11-21-03-53-43.pem
-rw-r--r-- 1 root root 2283 Nov 21 03:53 kubelet.crt
-rw------- 1 root root 1679 Nov 21 03:53 kubelet.key
subject=O = system:nodes, CN = system:node:k8s-cp.lab
notAfter=Nov 21 03:53:43 2027 GMT
```

Le kubelet garde ses certificats clients datés, et `kubelet-client-current.pem`
est un lien vers le plus récent. Son sujet le place dans le groupe
`system:nodes`, avec le nom `system:node:k8s-cp.lab`. Avant l'échéance, le
kubelet demande lui-même un nouveau certificat par une CSR, et déplace le
lien. Les dernières CSR du cluster sont justement celles des kubelets :

```bash
kubectl get csr --sort-by=.metadata.creationTimestamp -o custom-columns=NOM:.metadata.name,DEMANDEUR:.spec.username,SIGNATAIRE:.spec.signerName,ETAT:.status.conditions[0].type | tail -3
```

```text
csr-6km7w   system:bootstrap:67mfev   kubernetes.io/kube-apiserver-client-kubelet   Approved
csr-qx7l5   system:bootstrap:r5onmt   kubernetes.io/kube-apiserver-client-kubelet   Approved
csr-j6mvr   system:bootstrap:lzfpy6   kubernetes.io/kube-apiserver-client-kubelet   Approved
```

Demandées pendant l'amorçage (`system:bootstrap:…`), pour le signataire des
clients kubelet, et approuvées d'office. `kubeadm certs renew` ne s'occupe pas
de ce certificat.

## 🧪 Exercice 3 : renouveler sur une copie

Copiez la PKI dans `/tmp/essai-pki`, puis lisez les échéances de la copie
(les premières lignes seulement) :

```bash
sudo cp -a /etc/kubernetes/pki /tmp/essai-pki; sudo kubeadm certs check-expiration --cert-dir /tmp/essai-pki 2>&1 | sed -n '1,6p'
```

```text
[check-expiration] Reading configuration from the "kubeadm-config" ConfigMap in namespace "kube-system"...
[check-expiration] Use 'kubeadm init phase upload-config kubeadm --config your-config-file' to re-upload it.

CERTIFICATE                EXPIRES                  RESIDUAL TIME   CERTIFICATE AUTHORITY   EXTERNALLY MANAGED
admin.conf                 Nov 21, 2027 03:53 UTC   364d            ca                      no      
apiserver                  Nov 19, 2027 14:18 UTC   363d            ca                      no      
```

Notez le numéro de série, la date de fin et l'empreinte de la clé publique du
certificat de l'API server dans la copie :

```bash
sudo openssl x509 -in /tmp/essai-pki/apiserver.crt -noout -serial -enddate; sudo openssl x509 -in /tmp/essai-pki/apiserver.crt -noout -pubkey | sha256sum | cut -c1-16
```

```text
serial=3C76ED4D00B086D9
notAfter=Nov 19 14:18:00 2027 GMT
02af5763b250ddb1
```

Renouvelez ce certificat dans la copie (`--cert-dir`) :

```bash
sudo kubeadm certs renew apiserver --cert-dir /tmp/essai-pki 2>&1 | tail -2
```

```text

certificate for serving the Kubernetes API renewed
```

Relisez les mêmes valeurs, et vérifiez que le certificat est toujours signé
par la même autorité :

```bash
sudo openssl x509 -in /tmp/essai-pki/apiserver.crt -noout -serial -enddate; sudo openssl x509 -in /tmp/essai-pki/apiserver.crt -noout -pubkey | sha256sum | cut -c1-16; sudo openssl verify -CAfile /tmp/essai-pki/ca.crt /tmp/essai-pki/apiserver.crt
```

```text
serial=70864233F15CAD27
notAfter=Nov 21 04:25:40 2027 GMT
1dd6692464cb1038
/tmp/essai-pki/apiserver.crt: OK
```

Nouveau numéro de série, nouvelle date de fin, un an plus tard. L'empreinte
de la clé publique a changé aussi : kubeadm 1.37 a fabriqué une nouvelle clé.
L'autorité, elle, n'a pas changé : la vérification répond `OK`. Les clients
qui font confiance à la CA continuent donc de faire confiance au nouveau
certificat. Vérifiez enfin que le vrai certificat n'a pas bougé :

```bash
sudo openssl x509 -in /etc/kubernetes/pki/apiserver.crt -noout -serial; echo "(le vrai certificat n'a pas changé)"
```

```text
serial=3C76ED4D00B086D9
(le vrai certificat n'a pas changé)
```

Même numéro de série qu'avant : seul le certificat de la copie a été
renouvelé.

## 🧹 Nettoyage

Supprimez la copie de la PKI. Elle contient les clés privées du cluster : ne
la laissez pas traîner.

```bash
sudo rm -rf /tmp/essai-pki
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset kubeadm-verifier-et-renouveler-les-certificats
dsoxlab check kubeadm-verifier-et-renouveler-les-certificats
```

```text
╭─ Résultat : kubeadm-verifier-et-renouveler-les-certificats ─╮
│  0 / 100 pts                                                │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                            │
╰─────────────────────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : relever l'échéance de l'autorité, puis renouveler
les vrais certificats du plan de contrôle sans casser le cluster.

```bash
dsoxlab run kubeadm-verifier-et-renouveler-les-certificats
dsoxlab challenge kubeadm-verifier-et-renouveler-les-certificats
```
