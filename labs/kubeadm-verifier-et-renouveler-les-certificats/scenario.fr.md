# Vérifier et renouveler les certificats d'un cluster kubeadm

## La situation

kubeadm signe les certificats du plan de contrôle pour un an. Un cluster qu'on
ne met jamais à jour finit par refuser ses propres composants le jour où ils
expirent. L'équipe veut vérifier les échéances, et renouveler sans attendre la
panne.

Vous êtes sur **`k8s-cp.lab`**, le plan de contrôle du cluster kubeadm, avec
`kubectl` configuré et les droits `sudo`.

## Ce que vous devez obtenir

1. Dans **`~/pki/reponses.yaml`** : la **date d'échéance de l'autorité de
   certification** du cluster (`ca`), au format `AAAA-MM-JJ`.
2. Les certificats du **plan de contrôle** sont **renouvelés** : ceux de l'API
   server, de ses clients vers le kubelet et vers etcd, du front-proxy, et ceux
   d'etcd.
3. **kube-controller-manager** et **kube-scheduler** tournent avec le
   **certificat client renouvelé** de leur kubeconfig.
4. Votre **`~/.kube/config`** porte le **certificat d'administration
   renouvelé**, et `kubectl` répond avec lui.

## Les repères utiles

- `kubeadm certs check-expiration` liste chaque certificat, son échéance et
  l'autorité qui l'a signé. `openssl x509 -noout -dates -in <fichier>` lit un
  certificat à la main.
- `kubeadm certs renew` renouvelle un certificat, ou tous.
- Les composants du plan de contrôle sont des **Pods statiques**. L'API server
  et etcd rechargent seuls leur certificat de service quand le fichier change ;
  le controller-manager et le scheduler ne relisent le certificat client de
  leur kubeconfig qu'à leur démarrage. Les manifestes vivent dans
  `/etc/kubernetes/manifests`, et le kubelet arrête un Pod statique dont le
  manifeste disparaît.
- Le renouvellement réécrit aussi `/etc/kubernetes/admin.conf`, mais pas la
  copie que vous en avez faite.

## Comment vous saurez que c'est bon

Les tests lisent l'état du nœud, pas les commandes tapées :

- la date notée dans `~/pki/reponses.yaml` est celle de l'autorité de
  certification du cluster ;
- le numéro de série de chaque certificat du plan de contrôle a changé depuis
  le lancement du lab ;
- le controller-manager et le scheduler ont démarré après la réécriture de
  leur kubeconfig ;
- votre `~/.kube/config` porte le même certificat que le nouvel
  `admin.conf`, et `kubectl` répond avec lui.

```bash
dsoxlab check kubeadm-verifier-et-renouveler-les-certificats
```
