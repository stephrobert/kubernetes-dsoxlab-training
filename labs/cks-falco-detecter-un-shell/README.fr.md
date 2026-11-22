# Écrire une règle Falco qui détecte un geste précis

La leçon montre comment Falco surveille les appels système, comment se lit une
règle, et comment en ajouter une. Ce cours ajoute trois gestes qu'elle ne
montre pas : retrouver le nom exact d'un champ, faire refuser une règle
fautive **avant** de redémarrer Falco, et lire une alerte champ par champ.

Vous travaillez avec une règle d'essai qui repère la création d'un fichier
`/tmp/marque*` dans le namespace `essai-falco`. Le challenge porte sur une
autre règle et d'autres namespaces : vous le ferez seul, à la fin.

Page associée : [Falco](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/falco/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-falco-detecter-un-shell
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Falco y tourne, installé par son paquet, et écrit
ses alertes en JSON dans `/var/log/falco/events.json`.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
22 novembre 2026.

## 🔎 Exercice 1 : le nom exact d'un champ

Une règle filtre sur des **champs** : le fichier ouvert, le Pod, le
namespace… Un nom approximatif fait échouer la règle. `falco --list` donne la
liste complète, avec une description :

```bash
sudo falco --list 2>/dev/null | grep -E '^k8s\.(ns|pod)\.name|^container\.name|^fd\.name ' | cut -c1-110
```

```text
fd.name                       FD full name. If the fd is a file, this field contains the full path. If the FD 
container.name                The container name. In instances of userspace container engine lookup delays, th
k8s.pod.name                  The Kubernetes pod name. This field is extracted from the container runtime sock
k8s.ns.name                   The Kubernetes namespace name. This field is extracted from the container runtim
```

Le namespace s'écrit `k8s.ns.name`, pas `k8s.namespace.name` comme on
l'écrirait de mémoire. Ces champs viennent du runtime de conteneurs du nœud :
Falco les lit sans interroger l'API server.

## ✅ Exercice 2 : une règle refusée avant le redémarrage

Un Falco qui redémarre sur une règle fautive refuse de démarrer, et plus rien
n'est surveillé. `falco -V` valide des fichiers de règles sans rien charger.
Écrivez une règle qui utilise le mauvais nom de champ, et validez-la seule :

```bash
cat > /tmp/essai.yaml <<'YAML'
- rule: Essai marque dans tmp
  desc: un fichier marque est créé dans /tmp d'un conteneur du namespace essai-falco
  condition: open_write and container and k8s.namespace.name = essai-falco and fd.name startswith /tmp/marque
  output: marque écrite (fichier=%fd.name ns=%k8s.ns.name pod=%k8s.pod.name cmd=%proc.cmdline)
  priority: NOTICE
YAML
sudo falco -V /tmp/essai.yaml 2>&1 | grep -oE 'LOAD_ERR_[A-Z]+ [^.]*\.' | head -2
```

```text
LOAD_ERR_VALIDATE (Error validating rule/macro/list/exception objects): Undefined macro 'open_write' used in filter.
```

Falco ne signale pas le champ, mais la macro `open_write`, inconnue. Elle est
définie dans les règles fournies, que vous n'avez pas passées à la
validation. Validez donc votre fichier **avec** les règles fournies, dans
l'ordre où Falco les charge :

```bash
sudo falco -V /etc/falco/falco_rules.yaml -V /tmp/essai.yaml 2>&1 | grep -E '^\.\.\.|^ +\^|^LOAD_ERR'; echo "validation : code ${PIPESTATUS[0]}"
```

```text
...tainer and k8s.namespace.name = essai-falco and fd.name startswith /tmp/marque
                                                                                ^
LOAD_ERR_COMPILE_CONDITION (Error compiling condition): filter_check called with nonexistent field k8s.namespace.name
validation : code 1
```

Cette fois, la vraie faute : le repère `^` pointe la fin de la condition, et
la dernière ligne nomme le champ inexistant. Code 1. Corrigez le champ et
validez de nouveau :

```bash
cat > /tmp/essai.yaml <<'YAML'
- rule: Essai marque dans tmp
  desc: un fichier marque est créé dans /tmp d'un conteneur du namespace essai-falco
  condition: open_write and container and k8s.ns.name = essai-falco and fd.name startswith /tmp/marque
  output: marque écrite (fichier=%fd.name ns=%k8s.ns.name pod=%k8s.pod.name cmd=%proc.cmdline)
  priority: NOTICE
YAML
sudo falco -V /etc/falco/falco_rules.yaml -V /tmp/essai.yaml 2>&1 | tail -1 | jq -c '[.falco_load_results[] | {name, successful}]'
```

```text
[{"name":"/etc/falco/falco_rules.yaml","successful":true},{"name":"/tmp/essai.yaml","successful":true}]
```

Les deux fichiers sont acceptés : vous pouvez redémarrer sans risque.

## 🚨 Exercice 3 : charger la règle, la déclencher, lire l'alerte

Installez la règle dans `/etc/falco/rules.d/`, que Falco lit au démarrage, et
redémarrez le service :

```bash
sudo install -m 0644 /tmp/essai.yaml /etc/falco/rules.d/essai.yaml; sudo systemctl restart falco-modern-bpf; sleep 15; systemctl is-active falco-modern-bpf
```

```text
active
```

Lancez un Pod d'essai sur `k8s-cp.lab`, là où Falco regarde, et créez-y un
fichier marque :

```bash
kubectl create namespace essai-falco; kubectl run marqueur -n essai-falco --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --overrides='{"spec":{"nodeName":"k8s-cp.lab","tolerations":[{"operator":"Exists"}]}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/marqueur -n essai-falco --timeout=90s; kubectl exec marqueur -n essai-falco -- touch /tmp/marque-1; sleep 5
```

```text
namespace/essai-falco created
pod/marqueur created
pod/marqueur condition met
```

Chaque alerte est une ligne JSON. `jq` en extrait la priorité, la règle et les
champs qui ont servi au message :

```bash
sudo grep '"rule":"Essai marque dans tmp"' /var/log/falco/events.json | tail -1 | jq -c '{priority, rule, champs: .output_fields | {"fd.name", "k8s.ns.name", "k8s.pod.name", "proc.cmdline"}}'
```

```text
{"priority":"Notice","rule":"Essai marque dans tmp","champs":{"fd.name":"/tmp/marque-1","k8s.ns.name":"essai-falco","k8s.pod.name":"marqueur","proc.cmdline":"touch /tmp/marque-1"}}
```

Tout ce qu'une investigation demande est là : le fichier, le namespace, le
Pod et la commande exacte. Ces champs, et non le texte du message, sont ce
qu'un outil de collecte d'alertes doit lire.

## 🧹 Nettoyage

Supprimez le namespace d'essai, retirez la règle, puis redémarrez Falco pour
qu'il l'oublie :

```bash
kubectl delete namespace essai-falco --wait=true --timeout=120s; sudo rm -f /etc/falco/rules.d/essai.yaml /tmp/essai.yaml; sudo systemctl restart falco-modern-bpf; sleep 10; systemctl is-active falco-modern-bpf; ls /etc/falco/rules.d/
```

```text
namespace "essai-falco" deleted
active
```

Falco est actif, et `rules.d/` ne contient plus rien.

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-falco-detecter-un-shell
dsoxlab check cks-falco-detecter-un-shell
```

```text
╭─ Résultat : cks-falco-detecter-un-shell ─╮
│  0 / 100 pts                             │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests         │
╰──────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une règle qui alerte dès qu'un shell s'ouvre dans un
namespace sensible, et pas dans les autres.

```bash
dsoxlab run cks-falco-detecter-un-shell
dsoxlab challenge cks-falco-detecter-un-shell
```
