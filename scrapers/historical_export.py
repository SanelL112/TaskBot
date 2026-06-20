import os
import json
import logging
import datetime
from googleapiclient.discovery import build
from canvasapi import Canvas
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(BASE_DIR, '..', 'token.json')
ARCHIVE_DIR = os.path.join(BASE_DIR, '..', 'offline_archive')

os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

def get_google_creds():
    from google.oauth2.credentials import Credentials
    if os.path.exists(TOKEN_PATH):
        from google_scraper import SCOPES
        return Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    return None

def export_all_google_docs():
    logger.info("Exporting ALL Google Docs...")
    creds = get_google_creds()
    if not creds: return
    
    drive_service = build('drive', 'v3', credentials=creds, cache_discovery=False)
    docs_service = build('docs', 'v1', credentials=creds, cache_discovery=False)
    
    query = "mimeType='application/vnd.google-apps.document' and trashed=false"
    
    docs_text = []
    page_token = None
    
    while True:
        results = drive_service.files().list(q=query, fields="nextPageToken, files(id, name)", pageSize=100, pageToken=page_token).execute()
        items = results.get('files', [])
        
        for item in items:
            try:
                doc = docs_service.documents().get(documentId=item['id']).execute()
                content = ""
                for element in doc.get('body', {}).get('content', []):
                    if 'paragraph' in element:
                        for pe in element['paragraph']['elements']:
                            if 'textRun' in pe:
                                content += pe['textRun']['content']
                docs_text.append(f"--- Google Doc: {item['name']} ---\n{content}\n")
            except Exception as e:
                pass
                
        page_token = results.get('nextPageToken')
        if not page_token:
            break
            
    with open(os.path.join(ARCHIVE_DIR, "google_docs_export.txt"), "w") as f:
        f.write("\n".join(docs_text))
    logger.info(f"Exported {len(docs_text)} Google Docs.")

def export_all_classroom():
    logger.info("Exporting ALL Google Classroom data...")
    creds = get_google_creds()
    if not creds: return
    
    service = build('classroom', 'v1', credentials=creds)
    courses = service.courses().list(courseStates=['ACTIVE']).execute().get('courses', [])
    
    dump = []
    for course in courses:
        dump.append(f"=== CLASSROOM COURSE: {course['name']} ===")
        # Announcements
        try:
            announcements = service.courses().announcements().list(courseId=course['id']).execute().get('announcements', [])
            for a in announcements:
                dump.append(f"Announcement: {a.get('text', '')}")
        except Exception: pass
        
        # Coursework
        try:
            works = service.courses().courseWork().list(courseId=course['id']).execute().get('courseWork', [])
            for w in works:
                dump.append(f"Assignment: {w.get('title', '')}\nDesc: {w.get('description', '')}")
        except Exception: pass
        
    with open(os.path.join(ARCHIVE_DIR, "classroom_export.txt"), "w") as f:
        f.write("\n".join(dump))

def export_all_canvas():
    logger.info("Exporting ALL Canvas data...")
    load_dotenv(os.path.join(BASE_DIR, '..', '.env'))
    API_URL = os.getenv("CANVAS_API_URL", "https://canvas.instructure.com")
    API_TOKEN = os.getenv("CANVAS_API_TOKEN")
    if not API_TOKEN: return
    
    canvas = Canvas(API_URL, API_TOKEN)
    user = canvas.get_current_user()
    courses = list(user.get_favorite_courses())
    
    dump = []
    for c in courses:
        dump.append(f"=== CANVAS COURSE: {c.name} ===")
        try:
            for assgn in c.get_assignments():
                dump.append(f"Assignment: {getattr(assgn, 'name', '')} (Due: {getattr(assgn, 'due_at', '')})")
                desc = getattr(assgn, 'description', '')
                if desc:
                    # Strip basic HTML tags
                    import re
                    clean = re.sub('<[^<]+?>', '', desc)
                    dump.append(f"Description: {clean}")
        except Exception: pass
        try:
            for page in c.get_pages():
                try:
                    p = c.get_page(page.url)
                    clean = re.sub('<[^<]+?>', '', getattr(p, 'body', ''))
                    dump.append(f"Page: {page.title}\n{clean}")
                except Exception: pass
        except Exception: pass
        
    with open(os.path.join(ARCHIVE_DIR, "canvas_export.txt"), "w") as f:
        f.write("\n".join(dump))

def export_all_gmail():
    logger.info("Exporting ALL recent Gmail...")
    creds = get_google_creds()
    if not creds: return
    
    service = build('gmail', 'v1', credentials=creds)
    # Pull the last 500 emails to serve as historical context
    results = service.users().messages().list(userId='me', maxResults=500).execute()
    messages = results.get('messages', [])
    
    dump = []
    for msg in messages:
        try:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject', 'From', 'Date']).execute()
            headers = msg_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            dump.append(f"Email from {sender}: {subject}")
        except Exception: pass
        
    with open(os.path.join(ARCHIVE_DIR, "gmail_export.txt"), "w") as f:
        f.write("\n".join(dump))

def run_all_exports():
    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)
    # Add project root to sys path so google_scraper can be imported
    import sys
    sys.path.append(BASE_DIR)
    
    export_all_google_docs()
    export_all_classroom()
    export_all_canvas()
    export_all_gmail()
    logger.info("Historical Export Complete.")

if __name__ == "__main__":
    run_all_exports()
