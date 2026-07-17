import os

backend_dockerfile = """
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port and bind to all network interfaces
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

frontend_dockerfile = """
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Build the Next.js static payload
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
"""

docker_compose = """
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: school_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - ops-network

  backend:
    build:
      context: ./backend
    ports:
      - "8000:8000"
    environment:
      # Network DNS routing inside the container bridge
      - SQLALCHEMY_DATABASE_URI=postgresql+asyncpg://postgres:password@db:5432/school_db
      - SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
      - ALGORITHM=HS256
      - ACCESS_TOKEN_EXPIRE_MINUTES=1440
    depends_on:
      - db
    networks:
      - ops-network

  frontend:
    build:
      context: ./frontend
    ports:
      - "3000:3000"
    environment:
      # Browser client resolves localhost. Server-side rendering would resolve backend:8000
      - NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
    depends_on:
      - backend
    networks:
      - ops-network

networks:
  ops-network:
    driver: bridge

volumes:
  postgres_data:
"""

def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

write_file("backend/Dockerfile", backend_dockerfile)
write_file("frontend/Dockerfile", frontend_dockerfile)
write_file("docker-compose.yml", docker_compose)

print("[+] Backend Dockerfile synthesized.")
print("[+] Frontend Dockerfile synthesized.")
print("[+] Docker Compose orchestration matrix defined.")