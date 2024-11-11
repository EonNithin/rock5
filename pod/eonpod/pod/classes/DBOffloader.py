import os
import threading
import time
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database connection details from environment variables
SOURCE_DB_URL = os.getenv('SOURCE_DB_URL') or "postgresql+psycopg2://learneon_dev:(gm6|CHj**ICqq8W}GAuT>(bu4jU@learneondev.cngyygccg89w.ap-south-1.rds.amazonaws.com:5432/learneondev"
LOCAL_DB_URL = os.getenv('LOCAL_DB_URL') or "postgresql+psycopg2://learneon_dev:12345@localhost:5432/local_eonpod_db"

Base = declarative_base()

class DBOffloader:
    def __init__(self):
        self.source_engine = self.get_engine(SOURCE_DB_URL)
        self.local_engine = self.get_engine(LOCAL_DB_URL)
        self.keep_running = True
        # Start a thread for daily offload on server start
        self.thread = threading.Thread(target=self.run_offload, daemon=True)
        self.thread.start()
        logger.info("Initialized DBOffloader and started background thread.")

    def get_engine(self, db_url):
        return create_engine(db_url)

    def get_session(self, engine):
        Session = sessionmaker(bind=engine)
        return Session()

    def migrate_data(self):
        """Performs the data migration from source to local database."""
        local_session = None  # Initialize here to ensure visibility in the `except` block
        try:
            table_order = ['school', 'staff', 'subject_group', 'teacher_subject_groups']

            # Begin transaction
            local_session = self.get_session(self.local_engine)
            for table in table_order:
                logger.info(f"Migrating table: {table}")

                # Read data from source
                with self.get_session(self.source_engine) as source_session:
                    data = source_session.execute(text(f"SELECT * FROM {table}")).fetchall()
                    logger.info(f"Data fetched for {table}")

                # Clear existing data in local table and insert new data
                local_session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                if data:
                    columns = [column for column in source_session.execute(text(f"SELECT * FROM {table}")).keys()]
                    insert_stmt = text(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join([':' + col for col in columns])})")

                    insertion_data = [{columns[i]: row[i] for i in range(len(columns))} for row in data]
                    logger.info(f"Inserting data into {table}")

                    local_session.execute(insert_stmt, insertion_data)
            local_session.commit()  # Commit transaction only if all tables are processed successfully

            logger.info("Data migration completed successfully.")

        except Exception as e:
            logger.error(f"Error during data migration: {str(e)}")
            if local_session:
                local_session.rollback()
            logger.info("Transaction rolled back due to error.")
        
        finally:
            if local_session:
                local_session.close()


    def run_offload(self):
        """Runs the offload process once when the server starts."""
        while self.keep_running:
            # Call the migration process
            logger.info("Starting DB offload on server start.")
            self.migrate_data()
            self.keep_running = False  # Run only once on server start

    def stop(self):
        """Stop the background thread."""
        self.keep_running = False
        self.thread.join()
        logger.info("DBOffloader background thread stopped.")
