FROM node:26-alpine AS build

ARG PUBLIC_API_BASE_URL=http://localhost:8080/api/v1
ARG PUBLIC_APP_ENVIRONMENT=local
ENV PUBLIC_API_BASE_URL=$PUBLIC_API_BASE_URL \
    PUBLIC_APP_ENVIRONMENT=$PUBLIC_APP_ENVIRONMENT

WORKDIR /workspace
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc tsconfig.base.json prettier.config.cjs ./
COPY apps/web ./apps/web
COPY packages/contracts ./packages/contracts
COPY packages/shared ./packages/shared
RUN pnpm install --frozen-lockfile && pnpm --filter kasta_web build

FROM node:26-alpine AS runtime

ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000

WORKDIR /workspace
COPY --from=build --chown=node:node /workspace /workspace
USER node
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=6 CMD node -e "fetch('http://127.0.0.1:3000/').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"
CMD ["node", "apps/web/build"]
