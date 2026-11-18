# App Shell image. Build from the repository root: docker build -f frontend/Dockerfile .
# The context is limited by frontend/Dockerfile.dockerignore.
FROM node:22-alpine AS builder

WORKDIR /app
# Pin pnpm to the CI version (.github/workflows/ci.yml). pnpm 11 needs Node 22.
RUN corepack enable && corepack prepare pnpm@11.22.0 --activate

# The frozen install needs every workspace manifest, so copy the context before installing.
COPY . .
RUN pnpm install --frozen-lockfile
RUN pnpm --filter frontend run build

FROM nginx:alpine
COPY --from=builder /app/frontend/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
