#!/bin/bash

# Run PostgreSQL commands to drop specific tables
echo "Running PostgreSQL commands..."
psql postgresql://learneon_dev:12345@localhost:5432/local_eonpod_db <<EOF
DROP TABLE IF EXISTS school CASCADE;
DROP TABLE IF EXISTS staff CASCADE;
DROP TABLE IF EXISTS subject_group CASCADE;
DROP TABLE IF EXISTS teacher_subject_groups CASCADE;
EOF

if [ $? -eq 0 ]; then
    echo "PostgreSQL commands executed successfully."
else
    echo "Failed to execute PostgreSQL commands. Check database connectivity and syntax. Continuing..."
fi

# Execute the shell script to set up the database
echo "Executing database setup script..."
DB_SETUP_SCRIPT="$HOME/eonpod-ai/pod/eonpod_setup_scripts/local DB Setup scripts/create_tables_in_DB.sh"
if [ -f "$DB_SETUP_SCRIPT" ]; then
    chmod +x "$DB_SETUP_SCRIPT"
    "$DB_SETUP_SCRIPT" || echo "Database setup script execution failed. Continuing..."
else
    echo "Database setup script not found: $DB_SETUP_SCRIPT. Continuing..."
fi
