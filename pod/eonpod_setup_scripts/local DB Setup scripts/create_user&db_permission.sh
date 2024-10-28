# Create user
echo "Creating user 'learneon_dev'..."
sudo -u postgres psql -c "CREATE USER learneon_dev WITH PASSWORD '12345';"
echo "User 'learneon_dev' created."

# Create database
echo "Creating database 'local_eonpod_db'..."
sudo -u postgres psql -c "CREATE DATABASE local_eonpod_db OWNER learneon_dev;"
echo "Database 'local_eonpod_db' created."

# Grant necessary permissions
echo "Granting privileges to 'learneon_dev'..."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE local_eonpod_db TO learneon_dev;"
sudo -u postgres psql -c "GRANT USAGE, CREATE ON SCHEMA public TO learneon_dev;"
sudo -u postgres psql -c "ALTER SCHEMA public OWNER TO learneon_dev;"
sudo -u postgres psql -c "GRANT ALL ON SCHEMA public TO learneon_dev;"
echo "Privileges granted."
