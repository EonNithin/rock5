
from pod.dbmodels.models import DATABASE_URL, Staff, SubjectGroup, Teacher_Subject_Groups, get_session


session = get_session(DATABASE_URL)


def get_staff_by_rfid(rfid):
    staff = session.query(Staff).filter_by(rfid=rfid).first()
    return staff
    
def get_staff_by_pin(pin):
    staff = session.query(Staff).filter_by(pin=pin).first()
    return staff

    
def get_teacher_subject_groups_by_staff(staff_member):
    subject_groups = session.query(Teacher_Subject_Groups) \
        .join(SubjectGroup, Teacher_Subject_Groups.subject_group_id == SubjectGroup.id) \
        .filter(Teacher_Subject_Groups.teacher_id == staff_member.id).all()
    return subject_groups
    
def first_row_of_staff_table():
    first_staff_member = session.query(Staff).first()  # Get the first staff member
    return first_staff_member
