# L'image de l'application « inventaire », telle qu'elle a ete ecrite dans
# l'urgence. Elle construit et elle tourne : c'est tout ce qu'on lui a demande.
FROM node:latest

RUN apt-get update && apt-get install -y curl

COPY . /app
WORKDIR /app

EXPOSE 22

CMD ["node", "server.js"]
