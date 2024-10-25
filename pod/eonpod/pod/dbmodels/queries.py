
from pod.dbmodels.models import DATABASE_URL, Staff, SubjectGroup, Teacher_Subject_Groups, get_session


def get_staff_by_rfid(session, rfid, school_id):
    staff = session.query(Staff).filter_by(rfid=rfid, school_id=school_id).first()
    return staff
    
def get_staff_by_pin(session, pin, school_id):
    staff = session.query(Staff).filter(Staff.pin == int(pin), Staff.school_id == school_id).first()
    return staff

    
def get_teacher_subject_groups_by_staff(session, staff_member):
    subject_groups = session.query(Teacher_Subject_Groups) \
        .join(SubjectGroup, Teacher_Subject_Groups.subject_group_id == SubjectGroup.id) \
        .filter(Teacher_Subject_Groups.teacher_id == staff_member.id).all()
    return subject_groups
    

def get_if_subject_is_language_by_title(session, school_id, title):
    """Fetch a SubjectGroup by its title."""
    subject_group = session.query(SubjectGroup).filter_by(title=title, school_id=school_id).first()
    is_language = subject_group.is_language_subject   
    return is_language


def first_row_of_staff_table(session):
    first_staff_member = session.query(Staff).first()  # Get the first staff member
    return first_staff_member
