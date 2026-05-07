FROM node:22-alpine AS builder

WORKDIR /app

ARG VITE_INFO_SERVE_BASE_URL=
ENV VITE_INFO_SERVE_BASE_URL=${VITE_INFO_SERVE_BASE_URL}

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
