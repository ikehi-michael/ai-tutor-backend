#!/bin/bash

# AI Tutor Backend Quick Setup Script
# This script automates the setup process

set -e  # Exit on error

echo "🚀 AI Tutor Backend Setup Script"
echo "================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Python is installed
echo "📋 Checking prerequisites..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed. Please install Python 3.9 or higher.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python found: $(python3 --version)${NC}"

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}⚠️  PostgreSQL not found. Please install PostgreSQL first.${NC}"
    echo "   macOS: brew install postgresql@15"
    echo "   Ubuntu: sudo apt install postgresql"
    exit 1
fi
echo -e "${GREEN}✅ PostgreSQL found${NC}"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠️  venv already exists, skipping...${NC}"
else
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi

# Activate virtual environment
echo ""
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet --no-user

# Install dependencies
echo ""
echo "📥 Installing dependencies (this may take a few minutes)..."
pip install -r requirements.txt --quiet --no-user
echo -e "${GREEN}✅ Dependencies installed${NC}"

# Check for .env file
echo ""
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file..."
    cp env.example .env
    
    # Generate secret key
    SECRET_KEY=$(openssl rand -hex 32)
    
    # Update .env with generated secret key
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your_secret_key_here_generate_with_openssl_rand_hex_32/$SECRET_KEY/" .env
    else
        # Linux
        sed -i "s/your_secret_key_here_generate_with_openssl_rand_hex_32/$SECRET_KEY/" .env
    fi
    
    echo -e "${GREEN}✅ .env file created with generated SECRET_KEY${NC}"
    echo -e "${YELLOW}"
    echo "⚠️  IMPORTANT: Please edit .env and add:"
    echo "   1. DATABASE_URL (your PostgreSQL connection string)"
    echo "   2. OPENAI_API_KEY (your OpenAI API key)"
    echo -e "${NC}"
else
    echo -e "${YELLOW}⚠️  .env file already exists, skipping...${NC}"
fi

# Create database (optional - requires user input)
echo ""
read -p "🗄️  Do you want to create the PostgreSQL database now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter database name (default: ai_tutor_db): " DB_NAME
    DB_NAME=${DB_NAME:-ai_tutor_db}
    
    read -p "Enter database user (default: ai_tutor_user): " DB_USER
    DB_USER=${DB_USER:-ai_tutor_user}
    
    read -s -p "Enter password for database user: " DB_PASS
    echo
    
    # Create database and user
    psql postgres <<EOF
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Database created successfully${NC}"
        
        # Update .env with database URL
        DB_URL="postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|DATABASE_URL=.*|DATABASE_URL=$DB_URL|" .env
        else
            sed -i "s|DATABASE_URL=.*|DATABASE_URL=$DB_URL|" .env
        fi
        echo -e "${GREEN}✅ .env updated with database URL${NC}"
    else
        echo -e "${YELLOW}⚠️  Database creation failed. You may need to create it manually.${NC}"
    fi
fi

# Run migrations
echo ""
read -p "🔄 Do you want to run database migrations now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating initial migration..."
    alembic revision --autogenerate -m "Initial database setup"
    
    echo "Applying migration..."
    alembic upgrade head
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Database migrations completed${NC}"
    else
        echo -e "${RED}❌ Migration failed. Check your DATABASE_URL in .env${NC}"
    fi
fi

# Summary
echo ""
echo "================================"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "================================"
echo ""
echo "📝 Next steps:"
echo "   1. Edit .env and add your OPENAI_API_KEY"
echo "   2. Verify DATABASE_URL is correct"
echo "   3. Run: source venv/bin/activate"
echo "   4. Run: uvicorn app.main:app --reload"
echo "   5. Visit: http://localhost:8000/docs"
echo ""
echo "📚 See SETUP_AND_TEST.md for detailed testing instructions"
echo ""


