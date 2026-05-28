FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Frontend needs VITE_RECOGNITION_SERVER_URL to point to the backend's exposed address.
# Using relative or host network URLs works best for client-side evaluation.
RUN npm run build

FROM nginx:alpine
# Copy built static files to Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# 만들어둔 설정 파일을 Nginx 설정 폴더로 덮어쓰기 복사합니다.
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]