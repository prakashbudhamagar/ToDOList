# ---- build stage: compile the React bundle with Vite ----
# The build context is the repo root (see docker-compose.yml), because the
# frontend is an npm workspace: the root package-lock.json owns the
# dependency tree, so `npm ci` must run from the root.
FROM node:22-alpine AS build

WORKDIR /app

# Root workspace files first, so this layer is reused when only the code changes.
COPY package.json package-lock.json ./
COPY frontend/package.json ./frontend/
COPY backend/package.json ./backend/
RUN npm ci

# Now the source, then build just the frontend workspace.
COPY frontend/ ./frontend/
RUN npm run build --workspace=frontend

# ---- runtime stage: nginx serves the bundle and proxies the API ----
FROM nginx:1.27-alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 80