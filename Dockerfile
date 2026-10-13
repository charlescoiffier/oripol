# Oripol : site statique déjà construit par le CI (web/build), servi par nginx sans privilèges, port 8080
FROM nginxinc/nginx-unprivileged:alpine
COPY --chown=nginx:nginx web/build /usr/share/nginx/html
EXPOSE 8080
