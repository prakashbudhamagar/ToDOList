# ---- build stage: compile the React bundle with Vite ----
FROM node:22-alpine AS build

WORKDIR /app

# npm ci installs exactly the versions pinned in package-lock.json.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- runtime stage: nginx serves the bundle and proxies the API ----
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80