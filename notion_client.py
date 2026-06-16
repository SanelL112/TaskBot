import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = "2fb09c49-e758-802d-b7b7-f3451e9ad5f7"

def add_task_to_notion(title, source=None, due_date=None, url=None):
    """Pushes a new task to the user's Tasks Tracker database."""
    if not NOTION_API_KEY or NOTION_API_KEY == "your_notion_api_key":
        logger.error("Notion API key not configured.")
        return False
        
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    desc = f"Source: {source}" if source else "Source: AI Assistant"
    if url:
        desc += f"\nURL: {url}"

    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Task name": {
                "title": [{"text": {"content": title}}]
            },
            "Description": {
                "rich_text": [{"text": {"content": desc}}]
            }
        }
    }
    
    # Notion expects ISO 8601 dates (e.g. 2026-06-20 or 2026-06-20T12:00:00Z)
    if due_date and due_date.lower() != "null":
        try:
            data["properties"]["Due date"] = {
                "date": {"start": due_date}
            }
        except Exception:
            pass
        
    try:
        res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)
        res.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to push to Notion: {e}")
        if 'res' in locals():
            logger.error(res.text)
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing Notion API Push...")
    if add_task_to_notion("Automated Task Push Test", "Bot Setup", "2026-06-25"):
        print("Success! Check your Notion Tasks Tracker.")
    else:
        print("Failed to push to Notion.")
