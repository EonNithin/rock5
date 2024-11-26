import os
import threading
import time
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')

# Load environment variables
load_dotenv(dotenv_path="base.env")
load_dotenv(dotenv_path="config.env", override=True)

# Database connection details from environment variables
SOURCE_DB_URL = os.getenv('SOURCE_DB_URL')
LOCAL_DB_URL = os.getenv('LOCAL_DB_URL')

logger.debug(f"\nSOURCE_DB_URL is: {SOURCE_DB_URL} \nLOCAL_DB_URL is: {LOCAL_DB_URL}")

Base = declarative_base()


class DBOffloader:
    def __init__(self):
        self.source_engine = self.get_engine(SOURCE_DB_URL)
        self.local_engine = self.get_engine(LOCAL_DB_URL)
        self.keep_running = threading.Event()
        self.keep_running.set()

        # Start a thread for daily offload on server start
        self.thread = threading.Thread(target=self.run_offload, daemon=True)
        self.thread.start()
        logger.info("Initialized DBOffloader and started background thread.")

    def get_engine(self, db_url):
        """Creates and returns a database engine, handling connection errors."""
        try:
            return create_engine(db_url)
        except Exception as e:
            logger.error(f"Failed to create engine for DB URL: {db_url}. Error: {str(e)}")
            raise

    def get_session(self, engine):
        """Creates a database session with error handling."""
        try:
            Session = sessionmaker(bind=engine)
            return Session()
        except Exception as e:
            logger.error(f"Failed to create session for engine: {engine}. Error: {str(e)}")
            raise

    def migrate_table(self, table, local_session, source_session):
        """Migrates a single table from source to local database."""
        try:
            logger.info(f"Migrating table: {table}")
            # Fetch data from source table
            data = source_session.execute(text(f"SELECT * FROM {table}")).fetchall()
            logger.info(f"Data fetched for {table}, rows: {len(data)}")

            # Truncate local table
            local_session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))

            # Insert new data if available
            if data:
                columns = [col for col in source_session.execute(text(f"SELECT * FROM {table}")).keys()]
                insert_stmt = text(
                    f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join([':' + col for col in columns])})")
                insertion_data = [{columns[i]: row[i] for i in range(len(columns))} for row in data]
                local_session.execute(insert_stmt, insertion_data)
                logger.info(f"Data inserted into {table}.")
        except SQLAlchemyError as e:
            logger.error(f"Error migrating table {table}: {str(e)}")
            local_session.rollback()
            logger.info(f"Rolled back changes for table {table} due to error.")

    def migrate_data(self):
        """Performs the data migration from source to local database."""
        local_session = None
        try:
            local_session = self.get_session(self.local_engine)
            table_order = ['school', 'staff', 'subject_group', 'teacher_subject_groups']

            for table in table_order:
                # Each table is migrated individually to handle errors in isolation
                with self.get_session(self.source_engine) as source_session:
                    self.migrate_table(table, local_session, source_session)

            local_session.commit()
            logger.info("Data migration completed successfully.")
        except Exception as e:
            logger.error(f"Unexpected error during data migration: {str(e)}")
            if local_session:
                local_session.rollback()
                logger.info("Transaction rolled back due to unexpected error.")
        finally:
            if local_session:
                local_session.close()

    def run_offload(self):
        """Runs the offload process once when the server starts."""
        while self.keep_running.is_set():
            try:
                logger.info("Starting DB offload on server start.")
                self.migrate_data()
            except Exception as e:
                logger.error(f"Error during DB offload: {str(e)}")
            finally:
                self.keep_running.clear()  # Exit after one run

    def stop(self):
        """Stop the background thread."""
        self.keep_running.clear()
        self.thread.join(timeout=10)
        if self.thread.is_alive():
            logger.warning("DBOffloader background thread did not stop within the timeout.")
        else:
            logger.info("DBOffloader background thread stopped.")
