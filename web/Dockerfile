# Production image for the Aegis Trader browser terminal (Nuxt 4, SSR disabled).
# syntax=docker/dockerfile:1.7

FROM node:22-alpine AS build
WORKDIR /app
ENV NUXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NUXT_TELEMETRY_DISABLED=1 \
    HOST=0.0.0.0 \
    PORT=3000
# Nitro node-server output (SPA shell + client assets).
COPY --from=build /app/.output ./.output
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
