# ---- build stage ----
FROM node:20-alpine AS build
WORKDIR /app

# Base URL baked at build time; override via --build-arg VITE_API_BASE_URL=...
ARG VITE_API_BASE_URL=http://localhost:5000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY package.json ./
RUN npm install --no-audit --no-fund

COPY tsconfig.json vite.config.ts tailwind.config.js postcss.config.js index.html ./
COPY public ./public
COPY src ./src

RUN npm run build

# ---- runtime stage ----
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
