"""Serveur témoin du lab k8s-faire-sortir-le-trafic-par-une-passerelle.

Lancé par le setup sur k8s-cp.lab, HORS du cluster net-* : c'est une vraie
destination externe pour lui. Il répond par l'adresse source qu'il voit, ce
qui dit par quel nœud la requête est sortie. Python standard, aucune
dépendance.
"""
import http.server


class Temoin(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        corps = f"{self.client_address[0]}\n".encode()
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
