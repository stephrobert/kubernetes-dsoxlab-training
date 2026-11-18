"""Serveur témoin du challenge k8s-challenge-reseau-avance.

Lancé par le setup sur k8s-cp.lab, HORS du cluster net-* : c'est une vraie
destination externe pour lui. Il répond par l'adresse source qu'il voit, et
écrit chaque requête dans son journal, une ligne par requête :

    <date ISO> <chemin demandé> <adresse source>

C'est ce journal que lit le test de la sortie : il dit par quel nœud la
requête est sortie, et le chemin, choisi par le test, dit quelle requête.
Python standard, aucune dépendance.
"""
import datetime
import http.server
import threading

JOURNAL = "/var/log/dsoxlab-temoin-reseau.log"
VERROU = threading.Lock()


class Temoin(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        source = self.client_address[0]
        ligne = f"{datetime.datetime.now(datetime.UTC).isoformat()} {self.path} {source}\n"
        with VERROU, open(JOURNAL, "a", encoding="utf-8") as journal:
            journal.write(ligne)
        corps = f"{source}\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def log_message(self, *args):
        pass


# Toutes les interfaces : le témoin doit être joignable depuis les nœuds net-*,
# sur le réseau des VM du lab. Il ne renvoie que l'adresse de l'appelant.
http.server.ThreadingHTTPServer(("0.0.0.0", 8090), Temoin).serve_forever()  # noqa: S104
