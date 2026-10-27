# The published map: static files plus an nginx weather cache. Coolify builds this file as is.
FROM nginx:1.27-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY site/index.html /usr/share/nginx/html/index.html
COPY site/render.webp /usr/share/nginx/html/render.webp
COPY site/map_files /usr/share/nginx/html/map_files
EXPOSE 80
