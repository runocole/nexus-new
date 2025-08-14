#!/bin/bash
# Script to reset database and apply UUID migrations

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Database user - explicitly set to postgres
DB_USER="postgres"
DB_NAME="lily_shop"

echo -e "${YELLOW}This script will reset your database and apply fresh migrations.${NC}"
echo -e "${RED}WARNING: All data will be lost!${NC}"
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo -e "${YELLOW}Operation cancelled.${NC}"
    exit 1
fi

# Ask for password
read -s -p "Enter PostgreSQL password for user '$DB_USER': " DB_PASSWORD
echo

# Export password for PostgreSQL commands
export PGPASSWORD="$DB_PASSWORD"

# 1. Drop database
echo -e "${YELLOW}Dropping database...${NC}"
dropdb -U $DB_USER $DB_NAME
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to drop database. It might not exist or you don't have permission.${NC}"
    read -p "Create new database anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]
    then
        echo -e "${YELLOW}Operation cancelled.${NC}"
        # Clear password from environment
        unset PGPASSWORD
        exit 1
    fi
fi

# 2. Create database
echo -e "${YELLOW}Creating new database...${NC}"
createdb -U $DB_USER $DB_NAME
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to create database. Check PostgreSQL permissions.${NC}"
    # Clear password from environment
    unset PGPASSWORD
    exit 1
fi

# Clear password from environment for security
unset PGPASSWORD

# 3. Remove old migrations (optional)
echo -e "${YELLOW}Do you want to remove old migrations? (recommended for clean start) (y/n)${NC}"
read -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo -e "${YELLOW}Removing old migrations...${NC}"
    # Keep __init__.py files
    find shop/migrations -type f -name "*.py" ! -name "__init__.py" -delete
    find ads/migrations -type f -name "*.py" ! -name "__init__.py" -delete
    find authentication/migrations -type f -name "*.py" ! -name "__init__.py" -delete
    echo -e "${GREEN}Old migrations removed.${NC}"
fi

# 4. Make new migrations
echo -e "${YELLOW}Creating new migrations...${NC}"
python3 manage.py makemigrations
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to create migrations. Check for errors in your models.${NC}"
    exit 1
fi

# 5. Apply migrations
echo -e "${YELLOW}Applying migrations...${NC}"
python3 manage.py migrate
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to apply migrations. Check the error messages above.${NC}"
    exit 1
fi

# 6. Create superuser
echo -e "${YELLOW}Do you want to create a superuser? (y/n)${NC}"
read -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    python3 manage.py createsuperuser
fi

echo -e "${GREEN}Database reset complete! Your application now uses UUID primary keys.${NC}"
echo -e "${YELLOW}Remember to update your URL patterns to use uuid:pk instead of int:pk${NC}"