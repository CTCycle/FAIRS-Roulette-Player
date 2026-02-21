FROM node:22.12.0-alpine3.20 AS build

WORKDIR /app/FAIRS/client

COPY FAIRS/client/package.json FAIRS/client/package-lock.json ./
RUN npm ci

COPY FAIRS/client ./

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

FROM nginx:1.27.4-alpine3.20

COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/FAIRS/client/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
