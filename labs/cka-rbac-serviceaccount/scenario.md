# Donner une identité à une application : ServiceAccount, Role, RoleBinding

## La situation

L'équipe applicative a déployé **`inventaire`** dans le namespace
**`app-team`** : un outil qui doit lister les Pods de son namespace pour en
tenir l'inventaire. Le Deployment est là, mais aucun Pod ne démarre. Le
manifeste déclare un ServiceAccount **`pod-reader`** que personne n'a créé,
et sans identité, le ReplicaSet ne peut rien lancer.

Vous êtes sur le control plane, avec `kubectl` configuré.

## Ce que vous devez obtenir

1. Le ServiceAccount **`pod-reader`** existe dans `app-team`, et le Pod
   d'`inventaire` tourne avec cette identité.

2. Un Role **`pod-reader-role`** dans `app-team`, qui autorise à lire les
   Pods : `get`, `list`, `watch`. Rien d'autre : ni les supprimer, ni les
   créer, ni toucher à une autre ressource.

3. Un RoleBinding **`pod-reader-binding`** dans `app-team`, qui donne ce
   Role au ServiceAccount.

4. Depuis le Pod, avec le jeton qu'il trouve dans
   `/var/run/secrets/kubernetes.io/serviceaccount`, lister les Pods
   d'`app-team` répond `200`. Supprimer un Pod, lire les Secrets, ou lister
   les Pods de `default` répondent `403`.

## Les repères utiles

Un Pod ne parle jamais à l'API en son nom propre : il présente le jeton de
son ServiceAccount, projeté dans un volume, et l'API l'identifie comme
`system:serviceaccount:<namespace>:<nom>`. C'est ce sujet, et pas un
utilisateur, que le RoleBinding doit nommer.

`kubectl auth can-i <verbe> <ressource> -n <namespace> --as
system:serviceaccount:app-team:pod-reader` répond `yes` ou `no` sans rien
créer. Le Pod, lui, a `curl`, le certificat de l'API et son jeton sous la
main : `kubectl exec` vous y mène.

Un ReplicaSet qui ne peut pas créer ses Pods le dit dans les events du
namespace, pas dans des logs qui n'existent pas encore.

## Comment vous saurez que c'est bon

Les tests lisent le Role et le RoleBinding, puis entrent dans le Pod et
interrogent l'API avec son jeton, pour ce qui doit passer comme pour ce qui
doit être refusé.

```bash
dsoxlab check cka-rbac-serviceaccount
```
