FROM node:22-alpine

ENV NODE_ENV=production \
    PORT=8080

WORKDIR /app
RUN corepack enable && addgroup -S resolve && adduser -S resolve -G resolve
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
RUN pnpm install --frozen-lockfile

COPY . .
ARG RESOLVE_API_URL
ENV RESOLVE_API_URL=${RESOLVE_API_URL}
RUN pnpm --dir apps/web build \
    && cp -r apps/web/.next/static apps/web/.next/standalone/apps/web/.next/static \
    && chown -R resolve:resolve /app

USER resolve
EXPOSE 8080
CMD ["sh", "-c", "node apps/web/.next/standalone/apps/web/server.js"]
