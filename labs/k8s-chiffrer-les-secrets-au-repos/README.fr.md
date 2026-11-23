# Chiffrer les Secrets au repos

La leçon montre qu'un Secret est écrit en clair dans etcd, comment demander à
l'API server de le chiffrer avant de l'écrire, pourquoi les Secrets déjà
présents doivent être réécrits, et comment limiter leur lecture par RBAC. Ce
cours vous fait faire ces gestes sur un vrai cluster kubeadm, avec un autre
fournisseur que le challenge (`aescbc`), puis vous fait revenir en arrière
proprement.

Vous travaillez dans le namespace `essai-secrets`, avec une configuration
rangée dans `/etc/kubernetes/essai-chiffrement`. Le challenge porte sur un
autre namespace, un autre fournisseur et d'autres droits : vous le ferez seul,
à la fin.

Page associée : [Protéger les Secrets Kubernetes](https://www.stephane-robert.info/docs/securiser/secrets/secrets-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-chiffrer-les-secrets-au-repos
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui fait tourner l'API
server et etcd. Votre kubectl vise déjà le cluster. **Gardez le même terminal
jusqu'au nettoyage** : la fonction et la clé définies plus bas n'existent que
dans lui.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
23 novembre 2026, avec Kubernetes v1.37.2 et etcd 3.7.0.

## 🔍 Exercice 1 : lire un Secret directement dans etcd

Créez le namespace d'essai et un Secret. Définissez ensuite une fonction
`etcd_get`, qui évite de répéter les trois certificats qu'etcdctl demande, et
lisez le Secret dans etcd :

```bash
kubectl create namespace essai-secrets
kubectl -n essai-secrets create secret generic essai-ancien --from-literal=mot=Essai-Ancien-1
etcd_get() { sudo etcdctl --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key get "$1" --print-value-only; }
etcd_get /registry/secrets/essai-secrets/essai-ancien | grep -a -o Essai-Ancien-1
etcd_get /registry/secrets/essai-secrets/essai-ancien | head -c 7 | tr -c '[:print:]' '.'; echo
```

```text
namespace/essai-secrets created
secret/essai-ancien created
Essai-Ancien-1
k8s....
```

La valeur se lit telle quelle dans etcd, sans passer par l'API ni par le RBAC.
La valeur stockée commence par `k8s` suivi d'octets illisibles (affichés ici
en points) : c'est la marque d'un objet **non chiffré**. L'option `-a` de grep
lui fait lire la valeur comme du texte, bien qu'elle soit binaire. Elle
remplace la commande `strings`, qui n'est pas installée sur ce nœud.

## 🔐 Exercice 2 : activer le chiffrement avec aescbc

Écrivez une configuration de chiffrement. Le **premier** fournisseur de la
liste chiffre les nouvelles écritures, et tous servent à relire : `aescbc` en
premier, `identity` (aucun chiffrement) ensuite pour relire ce qui est encore
en clair. La clé fait 32 octets, encodés en base64.

```bash
CLE=$(head -c 32 /dev/urandom | base64)
sudo mkdir -p /etc/kubernetes/essai-chiffrement
sudo tee /etc/kubernetes/essai-chiffrement/config.yaml >/dev/null <<EOF
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: essai1
              secret: $CLE
      - identity: {}
EOF
sudo chmod 600 /etc/kubernetes/essai-chiffrement/config.yaml
```

L'API server tourne dans un conteneur, décrit par le manifeste
`/etc/kubernetes/manifests/kube-apiserver.yaml`. Il faut lui ajouter deux
drapeaux (le chemin de la configuration, et son rechargement automatique),
puis le volume qui rend ce répertoire visible dans le conteneur. Sauvegardez
d'abord le manifeste **hors** de `/etc/kubernetes/manifests`, que le kubelet
surveille, puis modifiez-le avec un court programme Python :

```bash
sudo cp /etc/kubernetes/manifests/kube-apiserver.yaml /var/backups/kube-apiserver.avant-essai.yaml
sudo python3 - <<'PY'
import yaml
chemin = "/etc/kubernetes/manifests/kube-apiserver.yaml"
m = yaml.safe_load(open(chemin))
c = m["spec"]["containers"][0]
c["command"] += ["--encryption-provider-config=/etc/kubernetes/essai-chiffrement/config.yaml",
                 "--encryption-provider-config-automatic-reload=true"]
c["volumeMounts"].append({"name": "essai-chiffrement", "mountPath": "/etc/kubernetes/essai-chiffrement", "readOnly": True})
m["spec"]["volumes"].append({"name": "essai-chiffrement", "hostPath": {"path": "/etc/kubernetes/essai-chiffrement", "type": "DirectoryOrCreate"}})
open(chemin, "w").write(yaml.safe_dump(m, sort_keys=False))
PY
sleep 20; until kubectl get --raw /healthz >/dev/null 2>&1; do sleep 3; done; echo "API revenue"
```

```text
API revenue
```

Le kubelet a vu le manifeste changer et a recréé l'API server : il a répondu de
nouveau 44 secondes après la modification. Créez un second Secret et regardez
comment il est stocké :

```bash
kubectl -n essai-secrets create secret generic essai-nouveau --from-literal=mot=Essai-Nouveau-2
etcd_get /registry/secrets/essai-secrets/essai-nouveau | head -c 25; echo
etcd_get /registry/secrets/essai-secrets/essai-nouveau | grep -a -c Essai-Nouveau
```

```text
secret/essai-nouveau created
k8s:enc:aescbc:v1:essai1:
0
```

Le préfixe `k8s:enc:aescbc:v1:essai1:` nomme le fournisseur et la clé qui ont
chiffré la valeur, et la valeur n'apparaît plus une seule fois.

## ♻️ Exercice 3 : réécrire les Secrets déjà présents

`essai-ancien` a été écrit avant le chiffrement. Comptez combien de fois sa
valeur apparaît dans etcd, puis réécrivez les Secrets du namespace : `kubectl
replace` les renvoie à l'API server, qui les chiffre en les écrivant.

```bash
etcd_get /registry/secrets/essai-secrets/essai-ancien | grep -a -c Essai-Ancien
kubectl -n essai-secrets get secrets -o json | kubectl replace -f -
etcd_get /registry/secrets/essai-secrets/essai-ancien | head -c 25; echo
kubectl -n essai-secrets get secret essai-ancien -o jsonpath='{.data.mot}' | base64 -d; echo
```

```text
1
secret/essai-ancien replaced
secret/essai-nouveau replaced
k8s:enc:aescbc:v1:essai1:
Essai-Ancien-1
```

Avant la réécriture, la valeur était toujours en clair : changer la
configuration ne touche que les nouvelles écritures. Après, `essai-ancien`
porte le préfixe. Par l'API, rien ne change : l'API server déchiffre à la
lecture et rend `Essai-Ancien-1`.

## ↩️ Exercice 4 : revenir en arrière sans perdre un Secret

Pour retirer le chiffrement, on ne peut pas simplement enlever les drapeaux :
l'API server perdrait la clé, et ne saurait plus relire les Secrets chiffrés.
Il faut d'abord mettre `identity` **en premier**, en gardant `aescbc` pour
relire. Réécrivez la configuration, puis attendez que l'API server la relise
(il vérifie le fichier une fois par minute) :

```bash
sudo tee /etc/kubernetes/essai-chiffrement/config.yaml >/dev/null <<EOF
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - identity: {}
      - aescbc:
          keys:
            - name: essai1
              secret: $CLE
EOF
sleep 70
kubectl -n essai-secrets create secret generic essai-sonde --from-literal=mot=x
etcd_get /registry/secrets/essai-secrets/essai-sonde | head -c 7 | tr -c '[:print:]' '.'; echo
```

```text
secret/essai-sonde created
k8s....
```

Le nouveau Secret est de nouveau écrit en clair. Les Secrets déjà chiffrés le
restent tant qu'on ne les réécrit pas. Comptez-les dans tout le cluster,
réécrivez tous les Secrets, puis comptez de nouveau :

```bash
chiffres() { for cle in $(sudo etcdctl --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key get /registry/secrets/ --prefix --keys-only); do etcd_get "$cle" | head -c 8 | grep -q 'k8s:enc' && echo "$cle"; done | wc -l; }
chiffres
kubectl get secrets -A -o json | kubectl replace -f - | wc -l
chiffres
```

```text
2
18
0
```

Deux Secrets étaient chiffrés, `essai-ancien` et `essai-nouveau`. La
réécriture touche les 18 Secrets du cluster, et il n'en reste plus aucun
chiffré : rendre le manifeste d'origine ne fera plus rien perdre. Pendant que
le chiffrement était actif, tout Secret créé ailleurs dans le cluster a été
chiffré lui aussi : c'est pour cela que la réécriture porte sur tous les
namespaces.

## 👤 Exercice 5 : limiter la lecture au Secret près

Créez un ServiceAccount qui ne peut lire qu'`essai-nouveau`, puis demandez à
l'API server ce qu'il peut faire, en prenant son identité avec `--as` :

```bash
kubectl -n essai-secrets create serviceaccount essai-lecteur
kubectl -n essai-secrets create role essai-lecture --verb=get --resource=secrets --resource-name=essai-nouveau
kubectl -n essai-secrets create rolebinding essai-lecture --role=essai-lecture --serviceaccount=essai-secrets:essai-lecteur
S=--as=system:serviceaccount:essai-secrets:essai-lecteur
kubectl auth can-i get secret/essai-nouveau -n essai-secrets $S
kubectl auth can-i get secret/essai-ancien -n essai-secrets $S
kubectl auth can-i list secrets -n essai-secrets $S
```

```text
serviceaccount/essai-lecteur created
role.rbac.authorization.k8s.io/essai-lecture created
rolebinding.rbac.authorization.k8s.io/essai-lecture created
yes
no
no
```

Il lit `essai-nouveau`, et rien d'autre. Donnez-lui maintenant le seul verbe
`list`, qui a l'air inoffensif, et essayez :

```bash
kubectl -n essai-secrets create role essai-liste --verb=list --resource=secrets
kubectl -n essai-secrets create rolebinding essai-liste --role=essai-liste --serviceaccount=essai-secrets:essai-lecteur
kubectl -n essai-secrets get secrets $S -o jsonpath='{range .items[*]}{.metadata.name}={.data.mot}{"\n"}{end}'
kubectl -n essai-secrets get secret essai-ancien $S
```

```text
role.rbac.authorization.k8s.io/essai-liste created
rolebinding.rbac.authorization.k8s.io/essai-liste created
essai-ancien=RXNzYWktQW5jaWVuLTE=
essai-nouveau=RXNzYWktTm91dmVhdS0y
essai-sonde=eA==
Error from server (Forbidden): secrets "essai-ancien" is forbidden: User "system:serviceaccount:essai-secrets:essai-lecteur" cannot get resource "secrets" in API group "" in the namespace "essai-secrets"
```

Avec `list`, le compte reçoit la **valeur** de chaque Secret du namespace
(encodée en base64, pas chiffrée), alors que `get` sur `essai-ancien` lui est
toujours refusé. Ne donnez jamais `list` ni `watch` sur les Secrets à un
compte qui n'a besoin que d'un Secret.

## 🧹 Nettoyage

Plus aucun Secret n'est chiffré depuis l'exercice 4 : rendez le manifeste
d'origine, attendez que l'API server revienne, puis supprimez la
configuration, la sauvegarde et le namespace d'essai. Les deux dernières
commandes vérifient que le manifeste ne parle plus de chiffrement et que les
Secrets du cluster se lisent toujours :

```bash
sudo cp /var/backups/kube-apiserver.avant-essai.yaml /etc/kubernetes/manifests/kube-apiserver.yaml
sleep 20; until kubectl get --raw /healthz >/dev/null 2>&1; do sleep 3; done; echo "API revenue"
sudo rm -rf /etc/kubernetes/essai-chiffrement /var/backups/kube-apiserver.avant-essai.yaml
kubectl delete namespace essai-secrets --wait=true --timeout=120s
sudo grep -c encryption-provider /etc/kubernetes/manifests/kube-apiserver.yaml
kubectl get secrets -A --no-headers | wc -l
```

```text
API revenue
namespace "essai-secrets" deleted
0
15
```

Le manifeste est revenu à son état d'origine, et les 15 Secrets qui restent
se lisent. Quittez ensuite la machine et remettez le lab à zéro.
`dsoxlab reset` rejoue le nettoyage puis la préparation du lab : vous
retrouvez exactement l'état de départ du challenge. Il vous demande de
confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-chiffrer-les-secrets-au-repos
dsoxlab check k8s-chiffrer-les-secrets-au-repos
```

```text
╭─ Résultat : k8s-chiffrer-les-secrets-au-repos ─╮
│  0 / 100 pts                                   │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests               │
╰────────────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : chiffrer les Secrets au repos avec secretbox,
réécrire ceux d'un namespace où ils sont encore en clair, et réduire un
ServiceAccount au seul Secret dont il a besoin.

```bash
dsoxlab run k8s-chiffrer-les-secrets-au-repos
dsoxlab challenge k8s-chiffrer-les-secrets-au-repos
```
