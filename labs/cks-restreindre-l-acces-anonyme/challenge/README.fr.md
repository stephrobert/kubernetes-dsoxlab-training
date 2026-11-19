# Challenge : Fermer l'API server et le kubelet aux clients anonymes sans casser kubeadm join

## La situation

Vous êtes sur le control plane **`k8s-cp.lab`** d'un cluster kubeadm, avec
`kubectl` configuré et `sudo`. Un audit a trouvé trois portes ouvertes aux
clients **sans identifiant** :

- un client anonyme **lit les objets du cluster** : une ClusterRoleBinding
  donne un rôle au groupe `system:unauthenticated` ;
- le **kubelet** du control plane répond à un client anonyme sur le port
  `10250`, et l'autorise à tout faire ;
- l'API server tourne **sans le plugin d'admission `NodeRestriction`**, que
  kubeadm active pourtant.

Une contrainte : de nouveaux workers rejoindront ce cluster par
`kubeadm join` avec un jeton. Ce join doit continuer à marcher.

## Ce que vous devez obtenir

1. Un client anonyme n'atteint plus que les chemins de santé (`/livez`,
   `/readyz`, `/healthz`) et ce dont `kubeadm join` a besoin. Partout ailleurs,
   l'API server lui répond **401**. La configuration d'authentification vit
   dans **`/etc/kubernetes/authn-config.yaml`**.
2. Aucune liaison RBAC ne donne de droits aux clients anonymes, hormis
   `system:public-info-viewer`, que l'API server pose à son démarrage, et
   `kubeadm:bootstrap-signer-clusterinfo`, que kubeadm crée pour la lecture de
   `cluster-info`.
3. Le kubelet du control plane répond **401** à un client anonyme, et
   **délègue** ses décisions d'autorisation à l'API server.
4. Les identifiants du kubelet ne peuvent plus poser d'étiquette
   `node-restriction.kubernetes.io/` sur leur propre nœud.

## Les repères

`curl -sk` sans identifiant, avec `-w '%{http_code}'`, dit ce que l'API server
et le kubelet accordent à un client anonyme. Pour savoir ce que le RBAC lui laisse, posez la question en admin avec une
**SubjectAccessReview** (`user: system:anonymous`, `groups:
[system:unauthenticated]`) : `kubectl auth can-i --as=system:anonymous` échoue
toujours, l'anonyme n'ayant pas le droit de poser la question lui-même.

`--anonymous-auth=false` ferme tout, découverte de `kubeadm join` comprise :
le join réessaierait alors sans fin sur une erreur 401. Une
**AuthenticationConfiguration** permet de garder l'accès anonyme sur une
liste de chemins seulement.

L'API server est un **Pod statique** : le kubelet le recrée dès que son
manifeste change, et un manifeste invalide l'empêche de revenir. Gardez une
copie du manifeste **hors** de `/etc/kubernetes/manifests`, que le kubelet
surveille. Un fichier lu par l'API server doit être monté dans son Pod.

Les identifiants du kubelet sont dans `/etc/kubernetes/kubelet.conf`.

## Comment vous saurez que ça marche

Les tests interrogent l'API server et le kubelet sans identifiant, lisent les
liaisons RBAC du cluster, et essaient de poser une étiquette réservée avec les
identifiants du kubelet.

```bash
dsoxlab check cks-restreindre-l-acces-anonyme
```
