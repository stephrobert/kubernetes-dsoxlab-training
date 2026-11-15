# L'image du catalogue de la boutique, telle qu'elle a été écrite dans
# l'urgence. Elle construit et elle sert ses pages : c'est tout ce qu'on lui a
# demandé.
FROM nginx:latest

RUN apt-get update && apt-get install -y curl

COPY site/ /usr/share/nginx/html/

EXPOSE 22

CMD ["nginx", "-g", "daemon off;"]
