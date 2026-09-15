# Un agent sur chaque nœud, control plane compris

## La situation

L'équipe supervision veut un agent sur **chaque nœud** du cluster, qui
signale sa présence dans ses logs. Le control plane **`k8s-cp.lab`** est
protégé, comme il se doit, par le taint
`node-role.kubernetes.io/control-plane:NoSchedule` : rien ne s'y planifie
sans le dire explicitement. L'agent doit pourtant y tourner aussi.

Vous êtes sur le control plane, avec `kubectl` configuré. Le namespace
**`monitoring`** existe.

## Ce que vous devez obtenir

1. Un DaemonSet **`monitor-agent`** dans `monitoring`, image
   **`busybox:1.37`**, dont le conteneur écrit `heartbeat` dans ses logs
   toutes les soixante secondes, indéfiniment.

2. Ses Pods portent le label **`app: monitor`**.

3. Un Pod de ce DaemonSet tourne sur **chaque nœud**, `k8s-cp.lab` compris,
   **sans retirer le taint** du control plane.

## Les repères utiles

Un DaemonSet ne choisit pas les nœuds : il en met un partout où son Pod est
admis. Un taint `NoSchedule` refuse tout Pod qui ne le tolère pas, et c'est
dans le template du DaemonSet que la tolérance s'écrit, clé, opérateur et
effet, recopiés depuis ce que `kubectl describe node` affiche.

Un DaemonSet dont un nœud manque le dit dans son statut : le nombre de Pods
voulus, planifiés et prêts.

## Comment vous saurez que c'est bon

Les tests lisent le DaemonSet et son statut, le nœud de chaque Pod, le taint
du control plane, et les logs de chaque agent.

```bash
dsoxlab check cka-daemonset-all-nodes
```
