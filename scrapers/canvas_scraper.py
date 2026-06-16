import os
import logging
from canvasapi import Canvas
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
CANVAS_API_URL = os.getenv("CANVAS_API_URL", "https://canvas.instructure.com")
CANVAS_API_TOKEN = os.getenv("CANVAS_API_TOKEN")

def get_canvas_instance():
    if not CANVAS_API_TOKEN or CANVAS_API_TOKEN == "your_canvas_api_token":
        logger.error("CANVAS_API_TOKEN is not set in .env")
        return None
    return Canvas(CANVAS_API_URL, CANVAS_API_TOKEN)

def get_upcoming_assignments():
    """Fetch upcoming assignments from Canvas for the current user."""
    canvas = get_canvas_instance()
    if not canvas:
        return "Canvas API token not configured. Please add CANVAS_API_TOKEN to .env."

    try:
        user = canvas.get_current_user()
        courses = user.get_favorite_courses()
        
        assignments_text = []
        for course in courses:
            try:
                # Fetch assignments for the course that are upcoming
                assignments = course.get_assignments(bucket="upcoming")
                for assignment in assignments:
                    due_date = assignment.due_at if hasattr(assignment, 'due_at') and assignment.due_at else "No due date"
                    assignments_text.append(f"[{course.name}] {assignment.name} - Due: {due_date}")
            except Exception as e:
                logger.warning(f"Could not fetch assignments for {course.name}: {e}")

        if not assignments_text:
            return "No upcoming assignments found in your favorite courses!"
        
        return "📚 **Upcoming Canvas Assignments:**\n" + "\n".join(assignments_text)
    
    except Exception as e:
        logger.error(f"Error connecting to Canvas: {e}")
        return f"Error connecting to Canvas: {e}"

if __name__ == "__main__":
    # Allow testing the script directly
    logging.basicConfig(level=logging.INFO)
    print("Testing Canvas API connection...")
    print(get_upcoming_assignments())
