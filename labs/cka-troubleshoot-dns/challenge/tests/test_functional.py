"""Tests transposés de K8sExamLab.

Chaque test appelle la bibliothèque de checks héritée, conservée telle
quelle sous /opt/checks sur le nœud. Elle interroge le cluster avec
kubectl : c'est bien l'état du système qui est lu.
"""

from __future__ import annotations

import pytest

from conftest import lab_host, lab_target_host

DISPATCH = "/opt/checks/dispatch.sh"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _check(host, *args: str):
    """Joue un check hérité et rend (code de retour, sortie)."""
    cmd = " ".join(str(a) for a in args)
    res = host.run(f"sudo -E bash {DISPATCH} {cmd}")
    return res.rc, (res.stdout + res.stderr).strip()


def test_coredns_running(host):
    """CoreDNS has at least 1 running pod"""
    rc, sortie = _check(host, "coredns-running")
    assert rc == 0, f"CoreDNS has at least 1 running pod : {sortie}"

def test_dns_resolves(host):
    """DNS resolution works from client pod"""
    rc, sortie = _check(host, "dns-resolves", "app", "client", "web-svc.app.svc.cluster.local")
    assert rc == 0, f"DNS resolution works from client pod : {sortie}"

def test_service_reachable(host):
    """Client pod can reach web-svc via HTTP"""
    rc, sortie = _check(host, "http-reachable", "app", "client", "web-svc.app.svc.cluster.local")
    assert rc == 0, f"Client pod can reach web-svc via HTTP : {sortie}"
