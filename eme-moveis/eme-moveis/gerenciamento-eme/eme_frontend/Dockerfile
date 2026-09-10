# ============================================================
# Dockerfile — Frontend EME Móveis (React + Vite + Express)
# Multi-stage: builda os assets e o bundle do servidor, depois
# copia só o necessário para a imagem final de produção.
# ============================================================

# ---- Stage 1: build ----
FROM node:22-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- Stage 2: production ----
FROM node:22-slim AS production

WORKDIR /app
ENV NODE_ENV=production

# Apenas dependências de produção (express, http-proxy-middleware etc.)
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# Bundle do servidor já compilado e os assets estáticos do Vite
COPY --from=build /app/dist ./dist

RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/health', r => process.exit(r.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))"

CMD ["node", "dist/server.cjs"]
