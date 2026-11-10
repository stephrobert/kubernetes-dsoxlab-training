# Lire un cluster : quel composant fait quoi

## La situation

Un cluster kind nommé **`architecture`** fait tourner quatre Nodes : un control
plane et trois workers. Votre `kubectl` le vise déjà.

Dans le namespace **`architecture`**, deux objets vous attendent : un Pod nommé
**`temoin`**, et un Deployment nommé **`file-attente`** dont les Pods ne
démarrent jamais.

Tout ce que vous trouvez va dans le relevé **`~/architecture/releve.txt`**. Ses
clés y sont déjà : complétez la valeur après chaque deux-points, une valeur par
ligne.

## Ce que vous devez obtenir

1. **`noeud-control-plane`** porte le nom du Node qui héberge le control plane.

2. **`pod-apiserver`**, **`pod-etcd`**, **`pod-scheduler`** et
   **`pod-controller-manager`** portent les noms des Pods des quatre composants
   du control plane, tels qu'on les trouve dans `kube-system` ;
   **`role-apiserver`**, **`role-etcd`**, **`role-scheduler`** et
   **`role-controller-manager`** disent, en quelques mots à vous, ce que fait
   chacun.

3. Une ligne **`runtime-<nom du Node>`** par Node worker, qui porte le runtime
   de conteneurs de ce Node et sa version.

4. **`noeud-du-pod-temoin`** porte le Node qui a reçu le Pod `temoin`, et
   **`evenement-scheduled`** cite le message de l'événement qui le prouve.

5. Pour `file-attente`, **`cree-par`** nomme le composant qui a créé ses
   Pods, et **`n-agit-pas`** nomme le seul composant qui n'agit pas sur eux.
   Diagnostic seul : ne réparez pas le Deployment.

## Comment vous serez noté

Le challenge est noté en confrontant votre relevé à l'**état réel** du cluster,
jamais sur les commandes tapées. Les rôles sont jugés sur le sens, en français
ou en anglais : un rôle doit décrire la fonction de son propre composant, pas
répéter son nom. Le seuil est de 70 sur 100. Aucune consigne pas à pas : les
leçons du module Architecture ont tout enseigné.

Laissez le Pod `temoin` et le Deployment `file-attente` en l'état.

Les événements sont conservés **24 heures** sur ce cluster (une heure par
défaut dans Kubernetes). Après une pause plus longue, ceux du lab ont disparu :
`dsoxlab reset k8s-challenge-lire-un-cluster` repose la situation.

```bash
dsoxlab check  k8s-challenge-lire-un-cluster
dsoxlab submit k8s-challenge-lire-un-cluster
```
