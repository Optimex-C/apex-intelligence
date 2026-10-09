FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build
ENV NODE_ENV=production
CMD ["sh","-c","./node_modules/.bin/next start -H 0.0.0.0 -p ${PORT:-3000}"]
