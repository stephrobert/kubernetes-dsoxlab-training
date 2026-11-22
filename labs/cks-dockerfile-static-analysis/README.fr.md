# Analyser un Dockerfile avant de construire l'image

La leçon montre comment `trivy config` lit un Dockerfile et dit, constat par
constat, quoi corriger. Ce cours ajoute ce qu'il faut pour s'en servir au
quotidien : analyser aussi un manifeste Kubernetes avec le même outil, ne
garder que les constats graves, faire échouer une chaîne d'intégration par le
code de sortie, et écarter un constat de façon visible.

Vous travaillez dans le dossier `~/essai-recette`, avec une recette Python et
un manifeste de Pod. Le challenge porte sur un autre Dockerfile : vous le
ferez seul, à la fin.

Page associée : [Sécuriser la chaîne d'approvisionnement](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/supply-chain-security/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-dockerfile-static-analysis
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). `trivy` y est installé.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
22 novembre 2026, avec trivy 0.74.0.

Écrivez une recette Python et un manifeste de Pod privilégié dans un dossier
d'essai :

```bash
mkdir -p ~/essai-recette; cat > ~/essai-recette/Dockerfile <<'DF'
FROM python:3.13
RUN pip install flask
COPY app.py /app.py
CMD python /app.py
DF
cat > ~/essai-recette/pod.yaml <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: recette
spec:
  containers:
    - name: app
      image: python:3.13
      securityContext:
        privileged: true
YAML
trivy --version | head -1
```

```text
Version: 0.74.0
```

## 📄 Exercice 1 : la même analyse, sur un manifeste Kubernetes

`trivy config` ne lit pas que les Dockerfile : il reconnaît aussi les
manifestes Kubernetes, et les analyse avec ses propres règles. Lancez-le sur
le dossier :

```bash
trivy config --quiet ~/essai-recette 2>/dev/null | grep -E '^(Dockerfile|pod.yaml)|Failures|^[A-Z]+:|KSV-|DS-' | head -14
```

```text
Dockerfile (dockerfile)
Failures: 2 (UNKNOWN: 0, LOW: 1, MEDIUM: 0, HIGH: 1, CRITICAL: 0)
DS-0002 (HIGH): Specify at least 1 USER command in Dockerfile with non-root user as argument
DS-0026 (LOW): Add HEALTHCHECK instruction in your Dockerfile
pod.yaml (kubernetes)
Failures: 17 (UNKNOWN: 0, LOW: 11, MEDIUM: 3, HIGH: 3, CRITICAL: 0)
KSV-0001 (MEDIUM): Container 'app' of Pod 'recette' should set 'securityContext.allowPrivilegeEscalation' to false
KSV-0003 (LOW): Container 'app' of Pod 'recette' should add 'ALL' to 'securityContext.capabilities.drop'
KSV-0004 (LOW): Container 'app' of 'pod' 'recette' in 'default' namespace should set securityContext.capabilities.drop
KSV-0011 (LOW): Container 'app' of Pod 'recette' should set 'resources.limits.cpu'
KSV-0012 (MEDIUM): Container 'app' of Pod 'recette' should set 'securityContext.runAsNonRoot' to true
KSV-0014 (HIGH): Container 'app' of Pod 'recette' should set 'securityContext.readOnlyRootFilesystem' to true
KSV-0015 (LOW): Container 'app' of Pod 'recette' should set 'resources.requests.cpu'
KSV-0016 (LOW): Container 'app' of Pod 'recette' should set 'resources.requests.memory'
```

Deux fichiers, deux familles de constats. Ceux du Dockerfile commencent par
`DS-`, ceux du manifeste par `KSV-`. Le Pod en cumule 17 : pas d'utilisateur
non root, pas de limite de ressources, conteneur privilégié… Un seul outil
couvre ainsi la recette de l'image et la façon dont elle sera lancée.

## 🎯 Exercice 2 : ne garder que le grave

17 constats d'un coup noient l'essentiel. `--severity` filtre par gravité :

```bash
trivy config --quiet --severity HIGH,CRITICAL ~/essai-recette 2>/dev/null | grep -E 'Failures|KSV-|DS-' | head -8
```

```text
Failures: 1 (HIGH: 1, CRITICAL: 0)
DS-0002 (HIGH): Specify at least 1 USER command in Dockerfile with non-root user as argument
Failures: 3 (HIGH: 3, CRITICAL: 0)
KSV-0014 (HIGH): Container 'app' of Pod 'recette' should set 'securityContext.readOnlyRootFilesystem' to true
KSV-0017 (HIGH): Container 'app' of Pod 'recette' should set 'securityContext.privileged' to false
KSV-0118 (HIGH): pod recette in default namespace is using the default security context, which allows root privileges
```

Il reste un constat élevé sur le Dockerfile (aucun `USER` non root) et trois
sur le manifeste, dont le conteneur privilégié. C'est par eux qu'on commence.

## 🚦 Exercice 3 : faire échouer une chaîne d'intégration

Par défaut, `trivy config` sort en 0 même quand il trouve des constats : il
informe, il ne bloque rien. `--exit-code 1` le fait sortir en 1 dès qu'un
constat du niveau demandé reste. Comparez deux seuils :

```bash
trivy config --quiet --severity CRITICAL --exit-code 1 ~/essai-recette >/dev/null 2>&1; echo "critiques : code $?"; trivy config --quiet --severity HIGH --exit-code 1 ~/essai-recette >/dev/null 2>&1; echo "élevés : code $?"
```

```text
critiques : code 0
élevés : code 1
```

Aucun constat critique, donc code 0. Au moins un constat élevé, donc code 1 :
une chaîne d'intégration qui lance cette commande s'arrête là. Le seuil se
choisit par équipe, et il se relève au fur et à mesure des corrections.

## 🙈 Exercice 4 : écarter un constat, en le disant

Un constat qu'on accepte se note dans un fichier `.trivyignore`, un
identifiant par ligne, plutôt que de baisser le seuil pour tout le monde.
Écartez le premier constat trouvé, puis relancez l'analyse depuis le dossier :

```bash
ID=$(trivy config --quiet -f json ~/essai-recette 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print(sorted({m["ID"] for r in d.get("Results",[]) for m in r.get("Misconfigurations") or []})[0])'); echo "constat ignoré : $ID"; echo "$ID" > ~/essai-recette/.trivyignore; cd ~/essai-recette && trivy config --quiet . 2>/dev/null | grep -c "$ID"; echo "(occurrences restantes de $ID)"
```

```text
constat ignoré : DS-0002
0
(occurrences restantes de DS-0002)
```

`DS-0002` n'apparaît plus. Attention : trivy lit `.trivyignore` dans le
**répertoire courant**, pas dans le dossier analysé, d'où le `cd`. Le fichier
reste dans le dépôt, à côté du Dockerfile : quiconque le relit voit ce qui a
été écarté. Écarter un constat n'est pas le corriger, et ce n'est pas ce que
le challenge demande.

## 🧹 Nettoyage

Supprimez le dossier d'essai :

```bash
rm -rf ~/essai-recette
```

```text

```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-dockerfile-static-analysis
dsoxlab check cks-dockerfile-static-analysis
```

```text
╭─ Résultat : cks-dockerfile-static-analysis ─╮
│  0 / 100 pts                                │
│  ░░░░░░░░░░░░░░░░░░░░  0/1 tests            │
╰─────────────────────────────────────────────╯
```

0 sur 1 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un Dockerfile Node auquel l'analyse reproche cinq
constats, à corriger tous sans changer ce que fait l'image.

```bash
dsoxlab run cks-dockerfile-static-analysis
dsoxlab challenge cks-dockerfile-static-analysis
```
