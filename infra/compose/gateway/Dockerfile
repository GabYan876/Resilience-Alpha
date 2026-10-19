# Multi-étapes : build du front React, puis image Caddy qui le sert et route /auth et /me.
# Contexte de build attendu : racine du dépôt.
FROM node:20-slim AS build
WORKDIR /app
COPY pay-now/frontend/package.json pay-now/frontend/package-lock.json ./
RUN npm ci
COPY pay-now/frontend/ ./
RUN npm run build

FROM caddy:2-alpine
COPY infra/compose/gateway/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
