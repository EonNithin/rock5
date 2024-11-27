#!/bin/bash

# Define the database URL (not used in the script but defined for reference)
DATABASE_URL="postgresql://learneon_dev:12345@localhost:5432/local_eonpod_db"

# SQL statements to create tables
CREATE_SCHOOL_TABLE="CREATE TABLE IF NOT EXISTS school (
    id UUID PRIMARY KEY,
    school_name VARCHAR(256),
    city VARCHAR(256),
    branch VARCHAR(256),
    subdomain_key VARCHAR(256)  
);"

CREATE_STAFF_TABLE="CREATE TABLE IF NOT EXISTS staff (
    id UUID PRIMARY KEY,
    school_id UUID REFERENCES school(id) ON DELETE CASCADE,
    user_role VARCHAR(50) DEFAULT 'TEACHER',
    mobile_no VARCHAR(20),
    email VARCHAR(255),
    employee_id VARCHAR(255),  
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    rfid VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    pin INTEGER
);"

CREATE_SUBJECT_GROUP_TABLE="CREATE TABLE IF NOT EXISTS subject_group (
    id UUID PRIMARY KEY,
    school_id UUID REFERENCES school(id) ON DELETE CASCADE,
    title VARCHAR(255),
    class VARCHAR(50),
    subject VARCHAR(255),
    is_language_subject BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    section VARCHAR(8)
);"

CREATE_TEACHER_SUBJECT_GROUPS_TABLE="CREATE TABLE IF NOT EXISTS teacher_subject_groups (
    id SERIAL PRIMARY KEY,
    school_id UUID REFERENCES school(id) ON DELETE CASCADE,
    teacher_id UUID REFERENCES staff(id) ON DELETE CASCADE,
    subject_group_id UUID REFERENCES subject_group(id) ON DELETE CASCADE
);"

# Function to execute a SQL statement with error checking
function execute_sql() {
    sql_statement="$1"
    PGPASSWORD="12345" psql -h localhost -U "learneon_dev" -d "local_eonpod_db" -c "$sql_statement"
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to execute SQL statement: $sql_statement"
        exit 1
    fi
}

# Wait for the PostgreSQL service to start (optional, but can help)
sleep 5

# Create tables in sequence with feedback
echo "Creating tables..."
execute_sql "$CREATE_SCHOOL_TABLE"
echo "Table 'school' created."
execute_sql "$CREATE_STAFF_TABLE"
echo "Table 'staff' created."
execute_sql "$CREATE_SUBJECT_GROUP_TABLE"
echo "Table 'subject_group' created."
execute_sql "$CREATE_TEACHER_SUBJECT_GROUPS_TABLE"
echo "Table 'teacher_subject_groups' created."

# If all tables were created successfully
echo "All tables created successfully in your database."

