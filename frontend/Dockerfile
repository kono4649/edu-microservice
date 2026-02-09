FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY public ./public
COPY src ./src
ENV REACT_APP_BFF_URL=http://localhost:8000
CMD ["npm", "start"]
