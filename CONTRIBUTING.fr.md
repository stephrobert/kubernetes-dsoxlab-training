# Contribuer à kubernetes-dsoxlab-training

**Langue :** [English](./CONTRIBUTING.md) · [Français](./CONTRIBUTING.fr.md)

Ce dépôt est un **catalogue de labs** consommé par la CLI
[`dsoxlab`](https://github.com/stephrobert/dsoxlab). Les contributions sont de
nouveaux labs et des correctifs. La CLI vit dans son propre dépôt : n'ajoutez
pas de code moteur ici, et si vous butez sur une limite du moteur, ouvrez-y une
issue plutôt que de la contourner localement.

## Mise en place

```bash
uv tool install dsoxlab        # la CLI, outil externe
git clone https://github.com/stephrobert/kubernetes-dsoxlab-training.git
cd kubernetes-dsoxlab-training
ansible-galaxy collection install -r requirements.yml
pre-commit install --install-hooks
dsoxlab doctor                 # vérifier l'environnement
```

## La règle non négociable : un lab s'éprouve dans les deux sens

Un test qui passe ne prouve rien tant qu'on n'a pas vu **échouer** ce qui doit
échouer. Un lab dont les tests passent **avant** le travail ne mesure rien, et
c'est le défaut le plus coûteux du domaine parce qu'il ne se voit qu'ainsi.

```bash
python3 scripts/valider-labs.py --lab <id>
```

Le validateur photographie le cluster, pose l'état initial, vérifie que les
tests rendent **0**, joue la solution du formateur, vérifie qu'ils rendent
**100**, nettoie, rejoue, nettoie encore, puis compare le cluster à sa
photographie. Un namespace oublié, un `ClusterRole`, un taint ou un CoreDNS
laissé à zéro replica rend le lab **ROUGE** : ce n'est pas lui qui en paierait
le prix, c'est le lab suivant. Le verdict de chaque lab est consigné dans
[`validation-labs.json`](validation-labs.json), et le catalogue du README en
porte la date.

Les deux contrôles mécaniques ci-dessous ne disent **rien** de la justesse d'un
lab, mais ils refusent un lab non conforme avant qu'un humain ne le lise :

```bash
dsoxlab validate-structure                       # le contrat déclaratif
python3 scripts/check-labs-completude.py --check # ce qui reste à faire
```

## Les tests lisent l'état du système, jamais les commandes tapées

Le candidat arrive au résultat par le chemin qu'il veut. On interroge donc le
cluster et le nœud, pas un historique.

```python
# NON : on relit ce que l'apprenant a écrit
assert "apparmor_parser" in historique

# OUI : on interroge l'état réel
profils = json.loads(host.run("sudo aa-status --json").stdout)["profiles"]
assert profils["k8s-refuser-ecriture"] == "enforce"
```

Un test par affirmation, **dont un qui prouve vraiment**. Vérifier qu'un profil
est chargé et qu'un Pod le déclare ne prouve pas que le confinement agit : un
profil vide passerait. Le dernier test d'un lab doit exercer les deux côtés, ce
qui est interdit et ce qui reste permis.

## Anatomie d'un lab

```text
labs/<examen>-<sujet>/
├── lab.yaml                          # le contrat : level = domaine du blueprint,
│                                     # doc_url = la leçon jumelée
├── scenario.md                       # la situation et l'objectif, pas la solution
├── README.md                         # la fiche du lab
├── setup.yaml                        # pose l'état initial, inclut le socle
├── cleanup.yaml                      # défait le lab, LAISSE le cluster en place
├── fixtures/prepare.sh               # la situation, côté cluster
└── challenge/
    ├── hints.yaml                    # indices base64, bilingues, à coût croissant
    ├── solution.sh                   # la solution du formateur, rejouable
    └── tests/test_functional.py      # la preuve : l'état du cluster
```

`dsoxlab new lab <id> --runtime vm` crée le squelette. L'identifiant suit
`<examen>-<sujet>`, en minuscules : `cks-apparmor-confiner-un-pod`.

`level` reprend le **domaine officiel du blueprint** mot pour mot
(`troubleshooting`, `system-hardening`, `workloads-scheduling`…) : c'est ce qui
permet de répondre à la seule question qui pilote ce dépôt, « combien de
compétences de l'examen puis-je démontrer ? ».

`doc_url` pointe la leçon du blog que le lab éprouve. Un lab sans leçon jumelée
est un lab qui enseigne au lieu d'éprouver, et enseigner est le rôle du site.

## Quatre pièges, chacun a coûté un cycle de validation

Ils sont vérifiés par `tests/test_pieges_du_depot.py`, mais les connaître évite
d'attendre le hook pour les découvrir.

- **Tout `ssh` d'une solution porte `-n`.** La solution est lue par `bash -s`
  depuis l'entrée standard : sans `-n`, `ssh` avale le reste du script comme
  entrée, rien après lui ne s'exécute, et le script rend 0.
- **Tout `fixtures/prepare.sh` trace sur le nœud.** dsoxlab ne rend que
  « non-zero return code » quand un script de fixture échoue ; sans le journal,
  le diagnostic repart de zéro. Reprenez l'en-tête d'un lab existant.
- **Tout `setup.yaml` inclut le socle.** Il n'y a aucun point d'accroche après
  le provisionnement : le cluster n'existe que parce que chaque lab l'installe.
  Un lab qui oublie l'inclusion tourne tant qu'un autre est passé avant, et
  échoue seul sur un cluster neuf.
- **Tout namespace créé est supprimé au nettoyage.** Le cluster, lui, reste en
  place : c'est le namespace qui part.

## Style de rédaction

Le français du blog : clair, pragmatique, sans jargon inutile.

- **Pas d'emoji, pas de tiret cadratin** dans ce que l'apprenant lit :
  `scenario.md`, `README.md`, les indices, les messages d'assertion. Un hook le
  vérifie.
- **Les messages d'assertion enseignent.** Un test qui échoue doit dire ce qui
  ne va pas et pourquoi, pas seulement ce qui était attendu. C'est souvent le
  seul texte que l'apprenant lira attentivement.
- Le `scenario.md` décrit une **situation**, pas une liste de commandes. Un
  candidat reçoit un contexte et un objectif, jamais un mode d'emploi.
- Les indices sont **encodés en base64** et **bilingues**, quatre de coût
  croissant, du plus vague au plus explicite, sans jamais donner le YAML
  complet.

## Avant d'ouvrir une pull request

Les hooks font le travail si vous les avez installés. À la main :

```bash
pre-commit run --all-files                      # hygiène, lint, vérificateurs
pre-commit run --all-files --hook-stage pre-push # contrat + fraîcheur du README
python3 scripts/gen_catalog.py                  # régénère le catalogue du README
```

Le `README.md` doit lister **tous** les labs avec leur leçon jumelée. Le
catalogue est généré depuis les `lab.yaml` réels : lancez `gen_catalog.py` après
avoir ajouté ou renommé un lab. La CI et le hook `pre-push` refusent tous deux
un catalogue périmé.

## Conventions

- **Commits** : messages en français, sujet factuel qui dit ce qui a changé et
  pourquoi, pas de préfixe conventionnel. Le corps raconte ce qui a été
  **mesuré**, y compris les mesures jetées en route : elles valent souvent plus
  que le résultat.
- **Branche dédiée**, description claire, et le lab joué dans les deux sens
  avant de demander la revue.

## Sécurité

Les vulnérabilités se signalent en privé, jamais par une issue publique : voir
[`SECURITY.md`](SECURITY.md).
