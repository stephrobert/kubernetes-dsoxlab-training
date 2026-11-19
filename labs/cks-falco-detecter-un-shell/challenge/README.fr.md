# Challenge : Faire lever par Falco une alerte sur un shell ouvert dans un namespace protégé

## La situation

**Falco** tourne sur le control plane `k8s-cp.lab`, installé depuis le paquet
officiel avec la sonde eBPF moderne. Il n'a que ses **règles fournies**, dans
`/etc/falco/falco_rules.yaml`, et écrit ses alertes en JSON, une par ligne,
dans **`/var/log/falco/events.json`**. Il charge aussi tout fichier de règles
posé dans **`/etc/falco/rules.d/`**, au démarrage du service
`falco-modern-bpf.service`.

Dans le namespace **`paiements`**, le Pod **`caisse`** traite des paiements.
L'équipe sécurité veut savoir **immédiatement** si quelqu'un y ouvre un shell.
Le namespace **`accueil`** porte le Pod **`vitrine`**, qui n'est pas concerné :
un shell y est un geste ordinaire. Les deux Pods tournent sur `k8s-cp.lab`, là
où Falco regarde.

Vous êtes sur le control plane, avec `kubectl` configuré, et `sudo`.

## Ce que vous devez obtenir

1. Une règle Falco nommée exactement **`Shell dans paiements`**, de priorité
   **`CRITICAL`**, qui alerte dès qu'un **shell démarre** dans un conteneur du
   namespace `paiements`.
2. Un shell ouvert dans un conteneur d'un **autre** namespace ne déclenche
   **pas** cette règle.
3. Les **règles fournies** restent intactes : votre règle vit dans son propre
   fichier.

## Les repères

Une règle Falco tient en quelques clés : `rule`, `desc`, `condition`, `output`
et `priority`. La condition combine des **macros** livrées avec Falco (un
processus qui démarre, un conteneur, un processus de la famille des shells) et
des **champs** comme le namespace Kubernetes de l'événement.

Le fichier des règles fournies est remplacé à chaque mise à jour : on n'y
écrit pas. Une règle mal écrite empêche Falco de démarrer, et le journal du
service dit pourquoi. Après avoir posé un fichier, Falco doit être redémarré
pour le lire.

Attention à la règle livrée `Terminal shell in container` : elle n'alerte que
pour un shell **avec terminal**. La demande vise tout shell qui démarre, avec
ou sans terminal.

## Comment vous saurez que ça marche

Les tests ouvrent un shell dans `caisse`, puis dans `vitrine`, et lisent ce que
Falco a écrit dans son journal. Ils comparent aussi le fichier des règles
fournies à l'empreinte que le paquet en garde.

```bash
dsoxlab check cks-falco-detecter-un-shell
```
