import streamlit as st
import nltk
import spacy
import pandas as pd
import base64
import random
import time
import datetime
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
import io
from streamlit_tags import st_tags
from PIL import Image
import pymysql
from courses_list import ds_course, web_course, android_course, ios_course, uiux_course, resume_videos, interview_videos
import plotly.express as px
import os
import hashlib
import re

# Download NLTK and Spacy resources
nltk.download('stopwords')

# Load the SpaCy model manually
try:
    nlp = spacy.load("en_core_web_sm")
    print("SpaCy model loaded successfully!")
except Exception as e:
    st.error(f"Error loading SpaCy model: {e}")

# Database Configuration
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = 'Myfamily162@'
DB_NAME = 'sra'

# Admin Credentials (Hashed for security)
ADMIN_USER = "machine_learning_hub"
ADMIN_PASSWORD_HASH = hashlib.sha256("mlhub123".encode()).hexdigest()

# File Upload Directory
UPLOAD_DIR = "Uploaded_Resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Helper Functions
def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()

def fetch_yt_video(link):
    """Fetch YouTube video title."""
    try:
        import pafy
        video = pafy.new(link)
        return video.title
    except Exception as e:
        st.error(f"Error fetching video title: {e}")
        return "Video Title Unavailable"

def get_table_download_link(df, filename, text):
    """Generate a link to download a DataFrame as a CSV file."""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

def pdf_reader(file):
    """Extract text from a PDF file."""
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)
    with open(file, 'rb') as fh:
        for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
            page_interpreter.process_page(page)
        text = fake_file_handle.getvalue()
    converter.close()
    fake_file_handle.close()
    return text

def show_pdf(file_path):
    """Display a PDF file in the Streamlit app."""
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def course_recommender(course_list):
    """Recommend courses based on the user's skills."""
    st.subheader("**Courses & Certificates🎓 Recommendations**")
    no_of_reco = st.slider('Choose Number of Course Recommendations:', 1, 10, 4)
    random.shuffle(course_list)
    rec_course = []
    for c_name, c_link in course_list[:no_of_reco]:
        st.markdown(f"({len(rec_course) + 1}) [{c_name}]({c_link})")
        rec_course.append(c_name)
    return rec_course

def create_db_connection():
    """Create a connection to the MySQL database."""
    try:
        connection = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD)
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        connection.select_db(DB_NAME)
        return connection, cursor
    except Exception as e:
        st.error(f"Error connecting to the database: {e}")
        return None, None

def create_user_table(cursor):
    """Create the user_data table if it doesn't exist."""
    table_sql = """
    CREATE TABLE IF NOT EXISTS user_data (
        ID INT NOT NULL AUTO_INCREMENT,
        Name varchar(100) NOT NULL,
        Email_ID VARCHAR(50) NOT NULL,
        resume_score VARCHAR(8) NOT NULL,
        Timestamp VARCHAR(50) NOT NULL,
        Page_no VARCHAR(5) NOT NULL,
        Predicted_Field VARCHAR(25) NOT NULL,
        User_level VARCHAR(30) NOT NULL,
        Actual_skills VARCHAR(300) NOT NULL,
        Recommended_skills VARCHAR(300) NOT NULL,
        Recommended_courses VARCHAR(600) NOT NULL,
        PRIMARY KEY (ID)
    );
    """
    cursor.execute(table_sql)

def insert_data(cursor, name, email, res_score, timestamp, no_of_pages, reco_field, cand_level, skills, recommended_skills, courses):
    """Insert user data into the database."""
    insert_sql = """
    INSERT INTO user_data (Name, Email_ID, resume_score, Timestamp, Page_no, Predicted_Field, User_level, Actual_skills, Recommended_skills, Recommended_courses)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    rec_values = (name, email, str(res_score), timestamp, str(no_of_pages), reco_field, cand_level, skills, recommended_skills, courses)
    cursor.execute(insert_sql, rec_values)

def extract_resume_data(text):
    """Extract resume data using SpaCy and regex."""
    doc = nlp(text)
    
    # Extract name (first entity recognized as a PERSON)
    name = None
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            name = ent.text
            break
    
    # Extract email
    email = None
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    emails = re.findall(email_pattern, text)
    if emails:
        email = emails[0]
    
    # Extract phone number
    phone = None
    phone_pattern = r"\+?\d[\d -]{8,12}\d"
    phones = re.findall(phone_pattern, text)
    if phones:
        phone = phones[0]
    
    # Extract skills (case-insensitive comparison)
    skills = ["Python", "Java", "Machine Learning", "SQL", "Data Analysis", "Flask", "Django", "React", "JavaScript"]
    found_skills = [skill for skill in skills if skill.lower() in text.lower()]
    
    # Extract work experience and internships
    work_experience = []
    internship_experience = []
    
    # Split text into sections based on common headings
    sections = re.split(r'\n\s*\n', text)  # Split by double newlines
    for section in sections:
        if "work experience" in section.lower():
            work_experience.append(section.strip())
        if "internship" in section.lower() or "intern" in section.lower():  # Check for both "internship" and "intern"
            internship_experience.append(section.strip())
    
    return {
        "name": name,
        "email": email,
        "phone": phone,
        "skills": found_skills,  # Ensure this is a list
        "work_experience": work_experience,
        "internship_experience": internship_experience,
        "text": text
    }
# Streamlit App
def run():
    st.set_page_config(
        page_title="HELLO , I AM HERE",
        page_icon='./Logo/SRA_Logo.ico',
    )

    st.title("INTERSUME : INTELLIGENT GUIDE")
    st.sidebar.markdown("# Choose User")
    activities = ["Normal User", "Admin"]
    choice = st.sidebar.selectbox("Choose among the given options:", activities)

    img = Image.open('D:\INTERSUME\INTERSUME\OUR LOGO.png')
    img = img.resize((250, 250))
    st.image(img)

    # Database Connection
    connection, cursor = create_db_connection()
    if connection and cursor:
        create_user_table(cursor)

    if choice == 'Normal User':
        pdf_file = st.file_uploader("Choose your Resume", type=["pdf"])
        if pdf_file is not None:
            save_image_path = os.path.join(UPLOAD_DIR, pdf_file.name)
            with open(save_image_path, "wb") as f:
                f.write(pdf_file.getbuffer())
            show_pdf(save_image_path)

            try:
                # Extract text from the PDF
                resume_text = pdf_reader(save_image_path)
                
                # Analyze the resume text
                resume_data = extract_resume_data(resume_text)
                
                if resume_data:
                    st.header("**Resume Analysis**")
                    st.success("Hello " + (resume_data['name'] or "User"))
                    st.subheader("**Your Basic info**")
                    st.text(f"Name: {resume_data.get('name', 'N/A')}")
                    st.text(f"Email: {resume_data.get('email', 'N/A')}")
                    st.text(f"Contact: {resume_data.get('phone', 'N/A')}")

                    # Skill Recommendations
                    st.subheader("**Skills Recommendation💡**")
                    keywords = st_tags(
                        label='### Skills that you have',
                        text='See our skills recommendation',
                        value=resume_data.get('skills', []),  # Ensure this is a list
                        key='1'
                    )

                    # Course Recommendations
                    st.subheader("**Courses & Certificates🎓 Recommendations**")
                    no_of_reco = st.slider('Choose Number of Course Recommendations:', 1, 10, 4)
                    random.shuffle(ds_course)
                    rec_course = []
                    for c_name, c_link in ds_course[:no_of_reco]:
                        st.markdown(f"({len(rec_course) + 1}) [{c_name}]({c_link})")
                        rec_course.append(c_name)

                    # Resume Tips & Ideas
                    st.subheader("**Resume Tips & Ideas💡**")
                    resume_score = 0

                    # Check for Objective or Professional Summary
                    if 'objective' in resume_text.lower() or 'proffessional summary' in resume_text.lower():
                        resume_score += 20
                        st.markdown('''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Objective/Professional Summary</h4>''', unsafe_allow_html=True)
                    else:
                        st.markdown('''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add your career objective or professional summary, it will give your career intension to the Recruiters.</h4>''', unsafe_allow_html=True)

                    # Check for Declaration
                    if 'declaration' in resume_text.lower():
                        resume_score += 20
                        st.markdown('''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Declaration✍</h4>''', unsafe_allow_html=True)
                    else:
                        st.markdown('''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Declaration✍. It will give the assurance that everything written on your resume is true and fully acknowledged by you</h4>''', unsafe_allow_html=True)

                    # Check for Work Experience
                    if resume_data.get('work_experience'):
                        resume_score += 20
                        st.markdown('''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Work Experience👨‍💼</h4>''', unsafe_allow_html=True)
                    else:
                        st.markdown('''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Work Experience👨‍💼. It will show your professional background to the Recruiters.</h4>''', unsafe_allow_html=True)

                    # Check for Internships
                    if resume_data.get('internship_experience'):
                        resume_score += 20
                        st.markdown('''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Internships👨‍💻</h4>''', unsafe_allow_html=True)
                    else:
                        st.markdown('''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Internships👨‍💻. It will show your practical experience to the Recruiters.</h4>''', unsafe_allow_html=True)

                    # Check for Achievements
                    if 'achievements' in resume_text.lower():
                        resume_score += 20
                        st.markdown('''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Achievements🏅</h4>''', unsafe_allow_html=True)
                    else:
                        st.markdown('''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Achievements🏅. It will show that you are capable for the required position.</h4>''', unsafe_allow_html=True)

                    # Check for Projects
                    if 'projects' in resume_text.lower():
                        resume_score += 20
                        st.markdown('''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Projects👨‍💻</h4>''', unsafe_allow_html=True)
                    else:
                        st.markdown('''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Projects👨‍💻. It will show that you have done work related the required position or not.</h4>''', unsafe_allow_html=True)

                    # Resume Score
                    st.subheader("**Resume Score📝**")
                    st.markdown(
                        """
                        <style>
                            .stProgress > div > div > div > div {
                                background-color: #d73b5c;
                            }
                        </style>""",
                        unsafe_allow_html=True,
                    )
                    my_bar = st.progress(0)
                    score = 0
                    for percent_complete in range(resume_score):
                        score += 1
                        time.sleep(0.1)
                        my_bar.progress(percent_complete + 1)
                    st.success('** Your Resume Writing Score: ' + str(score) + '**')
                    st.warning("** Note: This score is calculated based on the content that you have added in your Resume. **")
                    st.balloons()

                    # Bonus Video for Resume Writing Tips
                    st.header("**Bonus Video for Resume Writing Tips💡**")
                    resume_vid = random.choice(resume_videos)
                    res_vid_title = fetch_yt_video(resume_vid)
                    st.subheader("✅ **" + res_vid_title + "**")
                    st.video(resume_vid)

                    # Bonus Video for Interview Tips
                    st.header("**Bonus Video for Interview👨‍💼 Tips💡**")
                    interview_vid = random.choice(interview_videos)
                    int_vid_title = fetch_yt_video(interview_vid)
                    st.subheader("✅ **" + int_vid_title + "**")
                    st.video(interview_vid)

                    # Insert data into the database
                    ts = time.time()
                    timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H:%M:%S')
                    insert_data(
                        cursor,
                        resume_data['name'],
                        resume_data['email'],
                        str(resume_score),
                        timestamp,
                        str(1),  # Placeholder for number of pages
                        "N/A",  # Placeholder for predicted field
                        "N/A",  # Placeholder for candidate level
                        str(resume_data.get('skills', [])),  # Default to empty list
                        "N/A",  # Placeholder for recommended skills
                        str(rec_course)  # Recommended courses
                    )
                    connection.commit()

            except Exception as e:
                st.error(f"Error processing resume: {e}")

    else:
        st.success('Welcome to Admin Side')
        ad_user = st.text_input("Username")
        ad_password = st.text_input("Password", type='password')
        if st.button('Login'):
            if ad_user == ADMIN_USER and hash_password(ad_password) == ADMIN_PASSWORD_HASH:
                st.success("Welcome Admin")
                cursor.execute('''SELECT * FROM user_data''')
                data = cursor.fetchall()
                df = pd.DataFrame(data, columns=['ID', 'Name', 'Email', 'Resume Score', 'Timestamp', 'Total Page', 'Predicted Field', 'User Level', 'Actual Skills', 'Recommended Skills', 'Recommended Course'])
                st.dataframe(df)
                st.markdown(get_table_download_link(df, 'User_Data.csv', 'Download Report'), unsafe_allow_html=True)
            else:
                st.error("Wrong ID & Password Provided")

if __name__ == "__main__":
    run()