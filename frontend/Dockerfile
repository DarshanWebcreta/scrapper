FROM node:20-alpine

WORKDIR /workspace

# Copy dependencies manifest
COPY package*.json ./

# Install npm dependencies
RUN npm install

# Copy source code
COPY . .

# Expose Vite dev port
EXPOSE 5173

# Run development server
CMD ["npm", "run", "dev"]
