# syntax=docker/dockerfile:1.6

##
# Front-end build stage
##
FROM node:20-alpine AS build

WORKDIR /app/web

# Install dependencies first for better caching
COPY web/package*.json ./
RUN npm install

# Copy source code
COPY web/ ./

# Copy datasets (ensures /data is available even if sync script was not run)
COPY data/ /app/data

RUN npm run build

##
# Runtime stage - serve static assets with nginx
##
FROM caddy:2.8-alpine AS runtime

WORKDIR /srv

# Caddy serves everything from /srv and we use a Caddyfile for SPA fallback
COPY docker/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/web/dist/ /srv/
COPY --from=build /app/data /srv/data

EXPOSE 8080
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
