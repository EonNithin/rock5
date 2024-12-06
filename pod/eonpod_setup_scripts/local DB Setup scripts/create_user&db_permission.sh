#!/bin/bash

# Create user
echo "Creating user 'learneon_dev'..."
sudo -u postgres psql -c "CREATE USER learneon_dev WITH PASSWORD '12345';"
if [ $? -eq 0 ]; then
    echo "User 'learneon_dev' created successfully."
else
    echo "Failed to create user 'learneon_dev'."
fi

# Create database
echo "Creating database 'local_eonpod_db'..."
sudo -u postgres psql -c "CREATE DATABASE local_eonpod_db OWNER learneon_dev;"
if [ $? -eq 0 ]; then
    echo "Database 'local_eonpod_db' created successfully."
else
    echo "Failed to create database 'local_eonpod_db'."
fi

# Grant necessary permissions
echo "Granting privileges to 'learneon_dev'..."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE local_eonpod_db TO learneon_dev;"
if [ $? -eq 0 ]; then
    echo "Privileges on database 'local_eonpod_db' granted successfully to 'learneon_dev'."
else
    echo "Failed to grant privileges on database 'local_eonpod_db' to 'learneon_dev'."
fi

sudo -u postgres psql -c "GRANT USAGE, CREATE ON SCHEMA public TO learneon_dev;"
if [ $? -eq 0 ]; then
    echo "Granted USAGE and CREATE privileges on schema 'public' to 'learneon_dev'."
else
    echo "Failed to grant USAGE and CREATE privileges on schema 'public' to 'learneon_dev'."
fi

sudo -u postgres psql -c "ALTER SCHEMA public OWNER TO learneon_dev;"
if [ $? -eq 0 ]; then
    echo "Ownership of schema 'public' transferred to 'learneon_dev'."
else
    echo "Failed to transfer ownership of schema 'public' to 'learneon_dev'."
fi

sudo -u postgres psql -c "GRANT ALL ON SCHEMA public TO learneon_dev;"
if [ $? -eq 0 ]; then
    echo "All privileges on schema 'public' granted to 'learneon_dev'."
else
    echo "Failed to grant all privileges on schema 'public' to 'learneon_dev'."
fi

echo "User and DB permissions Setup completed successfully."
