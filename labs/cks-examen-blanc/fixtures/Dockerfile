FROM node:latest

RUN apt-get update && apt-get install -y curl

COPY . /app
WORKDIR /app

EXPOSE 22

CMD ["node", "server.js"]
