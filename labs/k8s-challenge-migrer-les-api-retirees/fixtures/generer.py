"""Écrit le dépôt ~/plateforme du challenge k8s-challenge-migrer-les-api-retirees.

Six manifestes peuvent être écrits dans une API retirée : quatre d'entre eux,
tirés au sort, le sont. Les deux autres sont déjà dans leur version courante,
avec deux manifestes témoins (Service et ServiceAccount) qui n'ont jamais
changé. Le rapport attendu dépend donc du tirage.

Usage : python3 generer.py <dépôt> <mémoire>
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

NS = "plateforme"
NGINX = "nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"

# fichier : (API retirée, API courante, manifeste ancien, manifeste courant)
MANIFESTES: dict[str, tuple[str, str, str, str]] = {
    "deploiement.yaml": (
        "extensions/v1beta1", "apps/v1",
        f"""apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: registre
  namespace: {NS}
spec:
  replicas: 2
  template:
    metadata:
      labels:
        app: registre
    spec:
      containers:
        - name: registre
          image: {NGINX}
          ports:
            - containerPort: 80
""",
        f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: registre
  namespace: {NS}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: registre
  template:
    metadata:
      labels:
        app: registre
    spec:
      containers:
        - name: registre
          image: {NGINX}
          ports:
            - containerPort: 80
""",
    ),
    "politique-reseau.yaml": (
        "extensions/v1beta1", "networking.k8s.io/v1",
        f"""apiVersion: extensions/v1beta1
kind: NetworkPolicy
metadata:
  name: registre-entrant
  namespace: {NS}
spec:
  podSelector:
    matchLabels:
      app: registre
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: client
      ports:
        - protocol: TCP
          port: 80
""",
        "",
    ),
    "role.yaml": (
        "rbac.authorization.k8s.io/v1beta1", "rbac.authorization.k8s.io/v1",
        f"""apiVersion: rbac.authorization.k8s.io/v1beta1
kind: Role
metadata:
  name: deployeur
  namespace: {NS}
rules:
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "patch"]
""",
        "",
    ),
    "liaison.yaml": (
        "rbac.authorization.k8s.io/v1beta1", "rbac.authorization.k8s.io/v1",
        f"""apiVersion: rbac.authorization.k8s.io/v1beta1
kind: RoleBinding
metadata:
  name: deployeur
  namespace: {NS}
subjects:
  - kind: ServiceAccount
    name: deployeur
    namespace: {NS}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: deployeur
""",
        "",
    ),
    "priorite.yaml": (
        "scheduling.k8s.io/v1beta1", "scheduling.k8s.io/v1",
        """apiVersion: scheduling.k8s.io/v1beta1
kind: PriorityClass
metadata:
  name: plateforme-critique
value: 900000
globalDefault: false
description: "Services de la plateforme à garder en cas de manque de place"
""",
        "",
    ),
    "tranche.yaml": (
        "discovery.k8s.io/v1beta1", "discovery.k8s.io/v1",
        f"""apiVersion: discovery.k8s.io/v1beta1
kind: EndpointSlice
metadata:
  name: registre-externe-1
  namespace: {NS}
  labels:
    kubernetes.io/service-name: registre-externe
addressType: IPv4
ports:
  - name: http
    protocol: TCP
    port: 5000
endpoints:
  - addresses: ["10.20.30.40"]
    conditions:
      ready: true
    topology:
      topology.kubernetes.io/zone: zone-ouest
""",
        f"""apiVersion: discovery.k8s.io/v1
kind: EndpointSlice
metadata:
  name: registre-externe-1
  namespace: {NS}
  labels:
    kubernetes.io/service-name: registre-externe
addressType: IPv4
ports:
  - name: http
    protocol: TCP
    port: 5000
endpoints:
  - addresses: ["10.20.30.40"]
    conditions:
      ready: true
    zone: zone-ouest
""",
    ),
}

TEMOINS = {
    "service.yaml": f"""apiVersion: v1
kind: Service
metadata:
  name: registre-externe
  namespace: {NS}
spec:
  ports:
    - name: http
      port: 5000
      targetPort: 5000
""",
    "compte.yaml": f"""apiVersion: v1
kind: ServiceAccount
metadata:
  name: deployeur
  namespace: {NS}
""",
}


def courant(fichier: str) -> str:
    """Le manifeste courant : écrit à part, ou l'ancien avec la seule apiVersion changée."""
    ancienne, nouvelle, texte_ancien, texte_courant = MANIFESTES[fichier]
    return texte_courant or texte_ancien.replace(f"apiVersion: {ancienne}", f"apiVersion: {nouvelle}", 1)


def main() -> None:
    depot, memoire = Path(sys.argv[1]), Path(sys.argv[2])
    retires = sorted(random.sample(sorted(MANIFESTES), 4))
    for fichier, (_, _, texte_ancien, _) in MANIFESTES.items():
        (depot / fichier).write_text(texte_ancien if fichier in retires else courant(fichier))
    for fichier, texte in TEMOINS.items():
        (depot / fichier).write_text(texte)
    attendu = {f: [MANIFESTES[f][0], MANIFESTES[f][1]] for f in retires}
    memoire.write_text(json.dumps({"retires": attendu, "fichiers": sorted([*MANIFESTES, *TEMOINS])}))
    print("API retirées dans :", ", ".join(retires))


main()
