#!/bin/bash
#
# JM Baryani HQ - One-Click Deployment Script
# For: Linux Mint / Ubuntu / Debian based systems
# Usage: chmod +x deploy.sh && sudo ./deploy.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "=============================================="
echo "  🍚 JM BARYANI HQ - VPS DEPLOYMENT"
echo "=============================================="
echo -e "${NC}"

# --- Configuration ---
APP_DIR="/opt/jmbariani"
REPO_URL="https://github.com/ainizzatymomoo/JMBariani.git"
BRANCH="main"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root: sudo ./deploy.sh${NC}"
  exit 1
fi

# --- Step 1: System Update ---
echo -e "${YELLOW}[1/7] Updating system...${NC}"
apt-get update -qq
apt-get upgrade -y -qq

# --- Step 2: Install Docker ---
echo -e "${YELLOW}[2/7] Installing Docker...${NC}"
if command -v docker &> /dev/null; then
  echo -e "${GREEN}Docker already installed: $(docker --version)${NC}"
else
  # Install Docker dependencies
  apt-get install -y -qq \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common

  # Add Docker GPG key & repo
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

  # Detect Ubuntu codename (Linux Mint maps to Ubuntu)
  UBUNTU_CODENAME=$(grep UBUNTU_CODENAME /etc/os-release | cut -d= -f2)
  if [ -z "$UBUNTU_CODENAME" ]; then
    UBUNTU_CODENAME=$(grep VERSION_CODENAME /etc/os-release | cut -d= -f2)
  fi

  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME} stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  # Start Docker
  systemctl start docker
  systemctl enable docker

  echo -e "${GREEN}Docker installed: $(docker --version)${NC}"
fi

# --- Step 3: Install Docker Compose (standalone, if not plugin) ---
echo -e "${YELLOW}[3/7] Checking Docker Compose...${NC}"
if docker compose version &> /dev/null; then
  echo -e "${GREEN}Docker Compose available: $(docker compose version)${NC}"
elif command -v docker-compose &> /dev/null; then
  echo -e "${GREEN}Docker Compose (standalone): $(docker-compose --version)${NC}"
else
  echo "Installing Docker Compose standalone..."
  curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
  echo -e "${GREEN}Docker Compose installed${NC}"
fi

# --- Step 4: Install Git & Tesseract ---
echo -e "${YELLOW}[4/7] Installing dependencies...${NC}"
apt-get install -y -qq git tesseract-ocr tesseract-ocr-eng

# --- Step 5: Clone/Pull Repository ---
echo -e "${YELLOW}[5/7] Setting up application...${NC}"
if [ -d "$APP_DIR" ]; then
  echo "App directory exists. Pulling latest..."
  cd "$APP_DIR"
  git pull origin "$BRANCH" || true
else
  echo "Cloning repository..."
  git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
fi

# --- Step 6: Setup Environment ---
echo -e "${YELLOW}[6/7] Configuring environment...${NC}"
ENV_FILE="$APP_DIR/.env.production"

if [ ! -f "$ENV_FILE" ]; then
  # Generate random passwords
  DB_PASS=$(openssl rand -hex 16)
  SECRET_KEY=$(openssl rand -hex 32)

  cat > "$ENV_FILE" << EOF
# JM Baryani HQ - Production Environment
# Generated on $(date)

# Database
POSTGRES_USER=jmbariani
POSTGRES_PASSWORD=${DB_PASS}
POSTGRES_DB=jmbariani
DATABASE_URL=postgresql://jmbariani:${DB_PASS}@db:5432/jmbariani

# App
SECRET_KEY=${SECRET_KEY}
DEBUG=false
UPLOAD_DIR=/app/uploads
OCR_LANG=eng
TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

# Server
APP_PORT=8000
FRONTEND_PORT=3000
EOF

  echo -e "${GREEN}Environment file created: ${ENV_FILE}${NC}"
  echo -e "${YELLOW}⚠️  Save your DB password: ${DB_PASS}${NC}"
else
  echo -e "${GREEN}Environment file already exists${NC}"
fi

# --- Step 7: Build & Start ---
echo -e "${YELLOW}[7/7] Building and starting containers...${NC}"
cd "$APP_DIR"

# Use production compose file
docker compose -f docker-compose.prod.yml --env-file .env.production down 2>/dev/null || true
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# Wait for services to start
echo ""
echo -e "${BLUE}Waiting for services to start...${NC}"
sleep 10

# Health check
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Backend is running!${NC}"
else
  echo -e "${YELLOW}⏳ Backend still starting... (check: docker compose -f docker-compose.prod.yml logs backend)${NC}"
fi

# --- Done! ---
echo ""
echo -e "${GREEN}=============================================="
echo "  🍚 JM BARYANI HQ - DEPLOYED!"
echo "=============================================="
echo ""
echo "  Frontend:  http://$(hostname -I | awk '{print $1}'):3000"
echo "  Backend:   http://$(hostname -I | awk '{print $1}'):8000"
echo "  API Docs:  http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""
echo "  App Dir:   ${APP_DIR}"
echo "  Env File:  ${ENV_FILE}"
echo ""
echo "  Useful Commands:"
echo "    cd ${APP_DIR}"
echo "    docker compose -f docker-compose.prod.yml logs -f"
echo "    docker compose -f docker-compose.prod.yml restart"
echo "    docker compose -f docker-compose.prod.yml down"
echo ""
echo -e "=============================================="
echo -e "${NC}"
