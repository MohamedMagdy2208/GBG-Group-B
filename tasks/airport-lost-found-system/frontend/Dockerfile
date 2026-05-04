FROM node:22-alpine AS dev

WORKDIR /app
COPY package.json package-lock.json* ./
# Drop the host-generated lockfile to avoid npm bug #4828 with optional native binaries.
RUN rm -f package-lock.json && npm install --no-audit --no-fund && npm install --no-save @rollup/rollup-linux-x64-musl @esbuild/linux-x64
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]

FROM dev AS build
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:1.27-alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
