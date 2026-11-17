# Audience Studio image (TASK-0621, ADR-0005). Node 20 service, Helm port 8010.
#
# Build from the repository root so pnpm can read the workspace lockfile:
#   docker build -f services/audience_studio/Dockerfile -t runefoble/audience-studio:0.1.0 .
#
# `make images` runs this build and loads the image into the Kind cluster.

FROM node:20-alpine AS builder

WORKDIR /app
RUN corepack enable

# Install only the audience-studio workspace package from the frozen lockfile.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY services/audience_studio/package.json services/audience_studio/package.json
RUN pnpm --filter @runefoble/audience-studio install --frozen-lockfile

COPY services/audience_studio/tsconfig.json services/audience_studio/tsconfig.json
COPY services/audience_studio/src services/audience_studio/src
RUN pnpm --filter @runefoble/audience-studio run build

# Copy the compiled output and production dependencies into a fresh directory.
RUN pnpm --filter @runefoble/audience-studio deploy --prod /out

FROM node:20-alpine AS runtime

ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=8010

WORKDIR /app
COPY --from=builder /out/node_modules ./node_modules
COPY --from=builder /out/package.json ./package.json
COPY --from=builder /app/services/audience_studio/dist ./dist

USER node

EXPOSE 8010

CMD ["node", "dist/index.js"]
