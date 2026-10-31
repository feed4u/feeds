# syntax=docker/dockerfile:1.6

##
# Front-end build stage
##
FROM node:20-alpine AS build

WORKDIR /app/web

# The prebuild step runs `bash ../code/sync_web_data.sh`; alpine ships no bash.
RUN apk add --no-cache bash

# Install exactly what the committed lock records
COPY web/package*.json ./
RUN npm ci

# Copy source code
COPY web/ ./

# The sync script resolves its root from its own location (/app), so it needs
# code/ beside web/ and the dataset in /app/data/<vertical>.
COPY code/sync_web_data.sh /app/code/sync_web_data.sh
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
# dist/data is the filtered snapshot written by prebuild (no news_recent.json,
# feed_errors_*, promo_filtered_*). A mount at /srv/data overrides it.

EXPOSE 8080
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
