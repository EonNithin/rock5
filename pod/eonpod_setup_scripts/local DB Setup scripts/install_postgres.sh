# Install PostgreSQL 16 and necessary packages
echo "Installing PostgreSQL..."
sudo apt update
sudo apt install postgresql postgresql-client

# Start PostgreSQL service
echo "Starting PostgreSQL service..."
sudo systemctl start postgresql
sudo systemctl enable postgresql
