"""
Deployment Configuration Module

This module provides configuration for deploying the Ollama agent framework
to various environments, including Docker and cloud platforms.
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class DeploymentConfig:
    """
    Deployment configuration for the Ollama agent framework.
    
    Provides configuration for different deployment environments.
    """
    
    @staticmethod
    def get_docker_compose():
        """
        Get Docker Compose configuration.
        
        Returns:
            Docker Compose YAML content
        """
        return """
version: '3'

services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  agent:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ollama-agent
    ports:
      - "8000:8000"
    volumes:
      - ./config:/app/config
      - ./plugins:/app/plugins
      - ./temp:/app/temp
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - SMITHERY_API_KEY=${SMITHERY_API_KEY:-}
    depends_on:
      - ollama
    restart: unless-stopped

volumes:
  ollama_data:
"""
    
    @staticmethod
    def get_dockerfile():
        """
        Get Dockerfile configuration.
        
        Returns:
            Dockerfile content
        """
        return """
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ /app/src/
COPY config/ /app/config/

# Create necessary directories
RUN mkdir -p /app/plugins /app/temp

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose API port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "src.main"]
"""
    
    @staticmethod
    def get_requirements():
        """
        Get Python requirements.
        
        Returns:
            Requirements file content
        """
        return """
# Core dependencies
fastapi>=0.95.0
uvicorn>=0.21.0
pydantic>=1.10.7
aiohttp>=3.8.4
python-multipart>=0.0.6
psutil>=5.9.5

# Image processing
Pillow>=9.5.0

# Optional: ML dependencies
# torch>=2.0.0
# transformers>=4.28.1
"""
    
    @staticmethod
    def get_systemd_service():
        """
        Get systemd service configuration.
        
        Returns:
            Systemd service file content
        """
        return """
[Unit]
Description=Ollama Agent Service
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/ollama-agent-project
ExecStart=/usr/bin/python3 -m src.main /home/ubuntu/ollama-agent-project/config/settings.json
Restart=on-failure
Environment=PYTHONPATH=/home/ubuntu/ollama-agent-project
Environment=OLLAMA_BASE_URL=http://localhost:11434

[Install]
WantedBy=multi-user.target
"""
    
    @staticmethod
    def get_nginx_config():
        """
        Get Nginx configuration for reverse proxy.
        
        Returns:
            Nginx configuration file content
        """
        return """
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
"""
    
    @staticmethod
    def get_kubernetes_deployment():
        """
        Get Kubernetes deployment configuration.
        
        Returns:
            Kubernetes deployment YAML content
        """
        return """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama-agent
  labels:
    app: ollama-agent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ollama-agent
  template:
    metadata:
      labels:
        app: ollama-agent
    spec:
      containers:
      - name: ollama-agent
        image: your-registry/ollama-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: OLLAMA_BASE_URL
          value: "http://ollama-service:11434"
        - name: SMITHERY_API_KEY
          valueFrom:
            secretKeyRef:
              name: ollama-agent-secrets
              key: smithery-api-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        volumeMounts:
        - name: config-volume
          mountPath: /app/config
        - name: plugins-volume
          mountPath: /app/plugins
        - name: temp-volume
          mountPath: /app/temp
      volumes:
      - name: config-volume
        configMap:
          name: ollama-agent-config
      - name: plugins-volume
        persistentVolumeClaim:
          claimName: ollama-agent-plugins-pvc
      - name: temp-volume
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: ollama-agent-service
spec:
  selector:
    app: ollama-agent
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
"""
    
    @staticmethod
    def get_cloud_run_config():
        """
        Get Google Cloud Run configuration.
        
        Returns:
            Cloud Run configuration YAML content
        """
        return """
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: ollama-agent
spec:
  template:
    spec:
      containers:
      - image: gcr.io/your-project/ollama-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: OLLAMA_BASE_URL
          value: "https://your-ollama-instance.com"
        - name: SMITHERY_API_KEY
          valueFrom:
            secretKeyRef:
              name: ollama-agent-secrets
              key: SMITHERY_API_KEY
        resources:
          limits:
            cpu: "2"
            memory: "4Gi"
"""
    
    @staticmethod
    def get_heroku_procfile():
        """
        Get Heroku Procfile.
        
        Returns:
            Procfile content
        """
        return """
web: uvicorn src.api.server:app --host=0.0.0.0 --port=$PORT
"""
    
    @staticmethod
    def write_deployment_files(base_dir: str):
        """
        Write deployment files to disk.
        
        Args:
            base_dir: Base directory to write files to
        """
        files = {
            "docker-compose.yml": DeploymentConfig.get_docker_compose(),
            "Dockerfile": DeploymentConfig.get_dockerfile(),
            "requirements.txt": DeploymentConfig.get_requirements(),
            "deployment/systemd/ollama-agent.service": DeploymentConfig.get_systemd_service(),
            "deployment/nginx/ollama-agent.conf": DeploymentConfig.get_nginx_config(),
            "deployment/kubernetes/deployment.yaml": DeploymentConfig.get_kubernetes_deployment(),
            "deployment/cloud-run/service.yaml": DeploymentConfig.get_cloud_run_config(),
            "Procfile": DeploymentConfig.get_heroku_procfile()
        }
        
        for file_path, content in files.items():
            full_path = os.path.join(base_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, "w") as f:
                f.write(content.strip())
                
            logger.info(f"Created deployment file: {file_path}")
