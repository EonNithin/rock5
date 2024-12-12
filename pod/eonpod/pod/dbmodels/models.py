from sqlalchemy import create_engine, Column, String, Integer, BigInteger ,Boolean, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import uuid
import pandas as pd
import os
import datetime
from dotenv import load_dotenv

Base = declarative_base()

# Load environment variables from .env file
load_dotenv(dotenv_path="base.env")
load_dotenv(dotenv_path="config.env", override=True)

# Accessing the variables
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

# Create the database URL
DATABASE_URL = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


# Define SQLAlchemy Models
class School(Base):
    __tablename__ = 'school'
    id = Column(Integer, primary_key=True)
    school_name = Column(String)
    branch = Column(String)
    city = Column(String)
    subdomain_key = Column(String) 

    # Define the relationship with Staff
    staff_members = relationship("Staff", back_populates="school")
    subject_groups = relationship("SubjectGroup", back_populates="school")


class Staff(Base):
    __tablename__ = 'staff'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id = Column(String, ForeignKey('school.id'))
    user_role = Column(String)
    mobile_no = Column(String)
    email = Column(String)
    employee_id = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    rfid = Column(String)
    is_active = Column(Boolean, default=True)
    pin = Column(Integer)
    
    # Relationships
    school = relationship("School", back_populates="staff_members")


# Define the Teacher class here (example structure)
class Teacher(Base):
    __tablename__ = 'teacher'
    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)

    # Define any additional fields and relationships if necessary

class SubjectGroup(Base):
    __tablename__ = 'subject_group'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    class_name = Column('class', String)
    subject = Column(String)
    is_active = Column(Boolean, default=True)
    is_language_subject = Column(Boolean, default=False)
    school_id = Column(String, ForeignKey('school.id'))
    section = Column(String(8))  # Adding the section column with a max length of 8 characters

    # Correctly define relationships
    school = relationship("School", back_populates="subject_groups")
    teacher_subject_groups = relationship("Teacher_Subject_Groups", back_populates="subject_group")  # Use back_populates for consistency


class Teacher_Subject_Groups(Base):
    __tablename__ = 'teacher_subject_groups'
    id = Column(Integer, primary_key=True)
    teacher_id = Column(String, ForeignKey('staff.id'))
    subject_group_id = Column(Integer, ForeignKey('subject_group.id'))

    # Define relationships correctly
    teacher = relationship("Staff")  # Assuming there's a Staff model that represents teachers
    subject_group = relationship("SubjectGroup", back_populates="teacher_subject_groups")  # Reference back to SubjectGroup


# Create database session
def get_session(database_url):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
    

# def get_staff_by_rfid(rfid):
#     staff = session.query(Staff).filter_by(rfid=rfid).first()
#     return staff
    
# def get_staff_by_pin(pin):
#     staff = session.query(Staff).filter_by(pin=pin).first()
#     return staff
    
# def get_teacher_subject_groups_by_staff(staff_member):
#     subject_groups = session.query(Teacher_Subject_Groups) \
#         .join(SubjectGroup, Teacher_Subject_Groups.subject_group_id == SubjectGroup.id) \
#         .filter(Teacher_Subject_Groups.teacher_id == staff_member.id).all()
#     return subject_groups
    
# def first_row_of_staff_table():
#     first_staff_member = session.query(Staff).first()  # Get the first staff member
#     return first_staff_member

# # Example usage of the session
# if __name__ == "__main__":
#     session = get_session(DATABASE_URL)
#     try:
#         rfid_value = '3113090456'
#         staff_member = get_staff_by_rfid(rfid_value)

#         if staff_member:
#             print(f"First name: {staff_member.first_name}, Last name: {staff_member.last_name}")
#             subject_groups = get_teacher_subject_groups_by_staff(staff_member)
#             for group in subject_groups:
#                 print(f"Subject Group: {group.subject_group_id}")  # Assuming 'name' exists in SubjectGroup
#         else:
#             print("Staff member not found.")

#         # You can perform other database operations here within the 'try' block

#         session.commit()  # Commit changes to the database
#     except Exception as e:
#         print(f"An error occurred: {e}")
#         session.rollback()  # Roll back changes in case of errors
#     finally:
#         session.close()  # Ensure the session is closed
