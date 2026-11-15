"""test_functional.py : k8s-servir-une-gateway-en-https

Cinq tests, un par état demandé, dans l'ordre de l'énoncé. Ils lisent l'API du
cluster et ce que le listener PRÉSENTE réellement à un client TLS, jamais un
fichier de l'apprenant.

Pourquoi lire le certificat présenté, et pas seulement le Secret : un listener
peut référencer un Secret qui existe et rester servi par un autre certificat
(référence non résolue, listener refusé, nom SNI qui ne correspond à rien). La
seule preuve est la poignée de main TLS, comparée au Secret que cert-manager a
rangé.

Pourquoi `openssl verify` en plus de l'émetteur : un DN d'émetteur se recopie,
une signature non. Le certificat présenté doit se vérifier contre la CA du
setup, et rien d'autre.

La Gateway est jointe par l'adresse de cluster du Service qu'Istio crée pour
elle, depuis le control plane : kube-proxy y rend tout ClusterIP joignable, et
le cluster n'a pas de répartiteur de charge. Les PEM ne transitent jamais par
le test : ils sont lus et comparés sur le nœud, par des tubes kubectl | openssl.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "vitrine"
HOTE = "vitrine.formation.test"
EMETTEUR = "ca-formation"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
CA_FICHIER = "/tmp/dsoxlab-ca-formation.crt"  # noqa: S108 -- fichier jetable du test, sur le nœud
PRESENTE_FICHIER = "/tmp/dsoxlab-vitrine-presente.crt"  # noqa: S108 -- idem

# Istio programme la Gateway et cert-manager émet le certificat après
# notification : budget borné, pour ne pas recaler une correction juste.
BUDGET_S = 120
PAS_S = 4


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _json(host, args: str) -> dict:
    rc, sortie, _ = _kubectl(host, f"{args} -o json")
    if rc != 0 or not sortie:
        return {}
    return json.loads(sortie)


def _condition(conditions: list | None, type_: str) -> tuple[str, str]:
    """Rend (status, reason) d'une condition, ou ('', '') si elle manque."""
    for c in conditions or []:
        if c.get("type") == type_:
            return c.get("status", ""), c.get("reason", "")
    return "", ""


def _attendre(lire, pret, budget: float = BUDGET_S):
    """Relit tant que `pret` est faux, dans la limite du budget."""
    valeur = lire()
    fin = time.monotonic() + budget
    while not pret(valeur) and time.monotonic() < fin:
        time.sleep(PAS_S)
        valeur = lire()
    return valeur


def _listener_https(gw: dict) -> dict:
    """Le premier listener HTTPS sur 443 d'une Gateway, ou {}."""
    for ln in gw.get("spec", {}).get("listeners", []) or []:
        if ln.get("protocol") == "HTTPS" and ln.get("port") == 443:
            return ln
    return {}


def _gateway(host) -> dict:
    """La Gateway de classe istio de vitrine qui porte un listener HTTPS 443."""
    for gw in _json(host, f"-n {NAMESPACE} get gateways.gateway.networking.k8s.io").get("items", []):
        if gw.get("spec", {}).get("gatewayClassName") == "istio" and _listener_https(gw):
            return gw
    return {}


def _gateway_requise(host) -> dict:
    gw = _gateway(host)
    if not gw:
        pytest.fail(message(
            en=f"No Gateway of class istio with an HTTPS listener on port 443 in {NAMESPACE}.",
            fr=f"Aucune Gateway de classe istio portant un listener HTTPS sur le port 443 dans {NAMESPACE}.",
        ))
    return gw


def _secret_du_listener(gw: dict) -> str:
    """Le Secret de vitrine que référence le listener HTTPS, ou ''."""
    refs = (_listener_https(gw).get("tls") or {}).get("certificateRefs") or []
    if not refs:
        return ""
    ref = refs[0]
    if ref.get("kind", "Secret") != "Secret" or ref.get("namespace", NAMESPACE) != NAMESPACE:
        return ""
    return ref.get("name", "")


def _adresse_gateway(host, gw: dict) -> str:
    """L'adresse de cluster du Service qu'Istio a créé pour la Gateway."""
    nom = gw["metadata"]["name"]
    for selecteur in (f"gateway.networking.k8s.io/gateway-name={nom}", f"istio.io/gateway-name={nom}"):
        services = _json(host, f"-n {NAMESPACE} get svc -l {selecteur}").get("items", [])
        if services:
            return services[0].get("spec", {}).get("clusterIP", "")
    return ""


def _adresse_requise(host, gw: dict) -> str:
    ip = _adresse_gateway(host, gw)
    if not ip:
        pytest.fail(message(
            en=f"No Service created by Istio for Gateway {gw['metadata']['name']}: it is not deployed.",
            fr=f"Aucun Service créé par Istio pour la Gateway {gw['metadata']['name']} : elle n'est pas déployée.",
        ))
    return ip


def _empreinte_du_secret(host, nom: str) -> str:
    """Empreinte SHA-256 du premier certificat de tls.crt, calculée sur le nœud."""
    res = host.run(
        f"sudo {KUBECTL} -n {NAMESPACE} get secret {nom} -o jsonpath='{{.data.tls\\.crt}}'"
        " | base64 -d | openssl x509 -noout -fingerprint -sha256"
    )
    ligne = res.stdout.strip()
    return ligne.split("=", 1)[1].strip() if res.rc == 0 and "=" in ligne else ""


def _lire_presente(host, ip: str) -> tuple[str, str]:
    """(empreinte, détail) du certificat présenté sur ip:443 avec le SNI du lab.

    Le certificat est aussi écrit sur le nœud, pour `openssl verify`.
    """
    res = host.run(
        f"echo | timeout 15 openssl s_client -connect {ip}:443 -servername {HOTE} 2>/dev/null"
        f" | openssl x509 > {PRESENTE_FICHIER} 2>/dev/null"
        f" && openssl x509 -in {PRESENTE_FICHIER} -noout -fingerprint -sha256 -issuer -ext subjectAltName"
    )
    empreinte = ""
    for ligne in res.stdout.splitlines():
        if "Fingerprint=" in ligne:
            empreinte = ligne.split("=", 1)[1].strip()
    return empreinte, res.stdout


def _poser_la_ca(host) -> bool:
    """Écrit la CA du setup sur le nœud, lue dans son Secret de cert-manager."""
    res = host.run(
        f"sudo {KUBECTL} -n cert-manager get secret {EMETTEUR} -o jsonpath='{{.data.tls\\.crt}}'"
        f" | base64 -d > {CA_FICHIER} && test -s {CA_FICHIER}"
    )
    return res.rc == 0


# ----------------------------------------------------------------------
# 1. cert-manager a émis le certificat, dans le namespace de la Gateway.
# ----------------------------------------------------------------------
def test_le_certificat_est_emis_par_la_ca_de_la_formation(host):
    """Le Secret TLS d'un listener vit dans le namespace de la Gateway : c'est
    donc là que le Certificate doit être demandé, à la CA du setup."""
    def lire() -> list:
        return [
            c for c in _json(host, f"-n {NAMESPACE} get certificates.cert-manager.io").get("items", [])
            if HOTE in (c.get("spec", {}).get("dnsNames") or [])
        ]

    def bon(c: dict) -> bool:
        ref = c.get("spec", {}).get("issuerRef", {})
        pret = _condition(c.get("status", {}).get("conditions"), "Ready")[0]
        return ref.get("kind") == "ClusterIssuer" and ref.get("name") == EMETTEUR and pret == "True"

    certificats = lire()
    assert certificats, message(
        en=f"No cert-manager Certificate in {NAMESPACE} lists {HOTE} in its dnsNames. "
        "The listener's Secret must live in the Gateway's namespace: request the "
        "certificate there.",
        fr=f"Aucun Certificate de cert-manager dans {NAMESPACE} ne porte {HOTE} dans "
        "ses dnsNames. Le Secret du listener doit vivre dans le namespace de la "
        "Gateway : c'est là que le certificat se demande.",
    )

    certificats = _attendre(lire, lambda cs: any(bon(c) for c in cs))
    detail = ", ".join(
        f"{c['metadata']['name']} (issuerRef {c.get('spec', {}).get('issuerRef', {}).get('kind', '?')}/"
        f"{c.get('spec', {}).get('issuerRef', {}).get('name', '?')}, Ready="
        f"{_condition(c.get('status', {}).get('conditions'), 'Ready')[0] or 'absent'})"
        for c in certificats
    )
    assert any(bon(c) for c in certificats), message(
        en=f"Certificate(s) found but none is Ready and issued by the ClusterIssuer {EMETTEUR}: "
        f"{detail}. No Issuer of that name exists here: the kind must be ClusterIssuer. "
        "kubectl describe certificate tells why it is not ready.",
        fr=f"Certificate(s) trouvé(s), mais aucun n'est prêt et émis par le ClusterIssuer {EMETTEUR} : "
        f"{detail}. Il n'existe aucun Issuer de ce nom ici : le kind doit être ClusterIssuer. "
        "kubectl describe certificate dit pourquoi il n'est pas prêt.",
    )


# ----------------------------------------------------------------------
# 2. La Gateway porte un listener HTTPS résolu, et elle est programmée.
# ----------------------------------------------------------------------
def test_la_gateway_https_est_programmee(host):
    """Exister ne suffit pas. Une Gateway dont le Service attend une adresse de
    répartiteur que ce cluster n'a pas reste non programmée, et un listener
    dont le Secret est introuvable a ResolvedRefs=False."""
    gw = _gateway_requise(host)
    gw = _attendre(
        lambda: _gateway(host) or gw,
        lambda g: _condition(g.get("status", {}).get("conditions"), "Programmed")[0] == "True",
    )

    listener = _listener_https(gw)
    mode = (listener.get("tls") or {}).get("mode", "Terminate")
    assert mode == "Terminate" and _secret_du_listener(gw), message(
        en=f"The HTTPS listener of Gateway {gw['metadata']['name']} must terminate TLS (mode "
        f"Terminate, here {mode}) and reference a Secret of {NAMESPACE} in certificateRefs.",
        fr=f"Le listener HTTPS de la Gateway {gw['metadata']['name']} doit terminer le TLS (mode "
        f"Terminate, ici {mode}) et référencer un Secret de {NAMESPACE} dans certificateRefs.",
    )

    statut_ln = next(
        (s for s in gw.get("status", {}).get("listeners", []) or [] if s.get("name") == listener.get("name")), {}
    )
    resolu, raison_ln = _condition(statut_ln.get("conditions"), "ResolvedRefs")
    assert resolu == "True", message(
        en=f"The HTTPS listener's certificate reference is not resolved: ResolvedRefs="
        f"{resolu or 'absent'} ({raison_ln or 'no reason'}). Is the Secret named in certificateRefs "
        "the one cert-manager wrote (spec.secretName of the Certificate), in the same namespace?",
        fr=f"La référence de certificat du listener HTTPS n'est pas résolue : ResolvedRefs="
        f"{resolu or 'absent'} ({raison_ln or 'sans raison'}). Le Secret nommé dans certificateRefs "
        "est-il celui que cert-manager a écrit (spec.secretName du Certificate), dans le même namespace ?",
    )

    programmee, raison = _condition(gw.get("status", {}).get("conditions"), "Programmed")
    assert programmee == "True", message(
        en=f"Gateway {gw['metadata']['name']} is not programmed: Programmed={programmee or 'absent'} "
        f"({raison or 'no reason'}). This cluster has no load balancer: a Service of type "
        "LoadBalancer never gets an address. Ask Istio for a ClusterIP Service with the annotation "
        "networking.istio.io/service-type on the Gateway.",
        fr=f"La Gateway {gw['metadata']['name']} n'est pas programmée : Programmed={programmee or 'absent'} "
        f"({raison or 'sans raison'}). Ce cluster n'a pas de répartiteur de charge : un Service de type "
        "LoadBalancer n'obtient jamais d'adresse. Demandez à Istio un Service ClusterIP par l'annotation "
        "networking.istio.io/service-type sur la Gateway.",
    )


# ----------------------------------------------------------------------
# 3. Le listener présente le certificat que cert-manager a rangé.
# ----------------------------------------------------------------------
def test_le_listener_presente_le_certificat_emis(host):
    gw = _gateway_requise(host)
    secret = _secret_du_listener(gw)
    ip = _adresse_requise(host, gw)

    rc, sortie, _ = _kubectl(host, f"-n {NAMESPACE} get secret {secret} -o json") if secret else (1, "", "")
    annotations = json.loads(sortie).get("metadata", {}).get("annotations", {}) if rc == 0 and sortie else {}
    assert annotations.get("cert-manager.io/certificate-name"), message(
        en=f"The Secret {secret or '(none)'} referenced by the listener was not written by cert-manager "
        "(no cert-manager.io/certificate-name annotation). The lab asks for a certificate issued and "
        "renewed by cert-manager, not a Secret created by hand.",
        fr=f"Le Secret {secret or '(aucun)'} référencé par le listener n'a pas été écrit par cert-manager "
        "(pas d'annotation cert-manager.io/certificate-name). Le lab demande un certificat émis et "
        "renouvelé par cert-manager, pas un Secret créé à la main.",
    )

    attendu = _empreinte_du_secret(host, secret)
    presente, detail = _attendre(
        lambda: _lire_presente(host, ip), lambda v: bool(attendu) and v[0] == attendu, budget=60
    )
    assert presente, message(
        en=f"No TLS handshake on {ip}:443 with SNI {HOTE}: the listener presents nothing. Is the port "
        "443, the protocol HTTPS, and the hostname of the listener (if set) the lab's name?",
        fr=f"Aucune poignée de main TLS sur {ip}:443 avec le SNI {HOTE} : le listener ne présente rien. "
        "Le port est-il 443, le protocole HTTPS, et le hostname du listener (s'il est posé) le nom du lab ?",
    )
    assert presente == attendu, message(
        en=f"The listener presents a certificate ({presente}) that is not the one cert-manager stored "
        f"in {secret} ({attendu}).",
        fr=f"Le listener présente un certificat ({presente}) qui n'est pas celui que cert-manager a "
        f"rangé dans {secret} ({attendu}).",
    )
    assert f"DNS:{HOTE}" in detail, message(
        en=f"The presented certificate does not cover {HOTE}: {detail.strip()}",
        fr=f"Le certificat présenté ne couvre pas {HOTE} : {detail.strip()}",
    )


# ----------------------------------------------------------------------
# 4. Son émetteur est la CA interne, et la signature se vérifie.
# ----------------------------------------------------------------------
def test_l_emetteur_du_certificat_presente_est_la_ca(host):
    gw = _gateway_requise(host)
    ip = _adresse_requise(host, gw)
    assert _poser_la_ca(host), "La CA ca-formation du setup est introuvable : relancez dsoxlab run."

    empreinte, detail = _lire_presente(host, ip)
    verif = host.run(f"openssl verify -CAfile {CA_FICHIER} {PRESENTE_FICHIER}") if empreinte else None
    emetteur = next((ligne for ligne in detail.splitlines() if ligne.startswith("issuer")), "")
    assert verif is not None and verif.rc == 0 and "OK" in verif.stdout, message(
        en=f"The presented certificate does not verify against the internal CA "
        f"({emetteur or 'no certificate presented'}). It must be issued by the ClusterIssuer {EMETTEUR}.",
        fr=f"Le certificat présenté ne se vérifie pas contre la CA interne "
        f"({emetteur or 'aucun certificat présenté'}). Il doit être émis par le ClusterIssuer {EMETTEUR}.",
    )
    assert "CA de la formation" in emetteur, message(
        en=f"Unexpected issuer: {emetteur}",
        fr=f"Émetteur inattendu : {emetteur}",
    )


# ----------------------------------------------------------------------
# 5. Un vrai client HTTPS atteint l'application, en ne faisant confiance qu'à la CA.
# ----------------------------------------------------------------------
def test_la_vitrine_repond_en_https(host):
    """La preuve de bout en bout : TLS validé par la CA (pas de -k), puis la
    route qui mène à l'application. Une Gateway sans route rend 404."""
    gw = _gateway_requise(host)
    ip = _adresse_requise(host, gw)
    assert _poser_la_ca(host), "La CA ca-formation du setup est introuvable : relancez dsoxlab run."

    def demander() -> tuple[str, str]:
        res = host.run(
            f"curl -s --max-time 8 --cacert {CA_FICHIER} --resolve {HOTE}:443:{ip} "
            f"https://{HOTE}/ -w '|%{{http_code}}'"
        )
        corps, _, code = res.stdout.rpartition("|")
        return corps.strip(), code.strip()

    corps, code = _attendre(demander, lambda v: v[0] == "vitrine", budget=60)
    assert corps == "vitrine", message(
        en=f"https://{HOTE}/ through the Gateway answers code {code or 'none'}, body {corps!r}. "
        "Code 000: TLS failed or nothing listens. 404: no HTTPRoute attached to the listener sends "
        "this name to the Service vitrine.",
        fr=f"https://{HOTE}/ par la Gateway répond le code {code or 'aucun'}, corps {corps!r}. "
        "Code 000 : le TLS a échoué ou rien n'écoute. 404 : aucune HTTPRoute attachée au listener "
        "n'envoie ce nom vers le Service vitrine.",
    )
