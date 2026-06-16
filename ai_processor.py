"""
ai_processor.py
Spins up a one-shot Antigravity 'flash' conversation to filter and
structure raw scraped data into tasks (-> Notion) and alerts (-> Telegram).
"""

import json
import subprocess
import time
import os
import logging

logger = logging.getLogger(__name__)

AGENTAPI_BIN = os.getenv("AGENTAPI_BIN", "/home/sanellathiya/.gemini/antigravity-cli/bin/agentapi")
TRANSCRIPT_BASE = os.path.expanduser("~/.gemini/antigravity-cli/brain")

SYSTEM_PROMPT = """
You are a personal assistant AI. You will receive raw data scraped from several sources.

Your job is to filter out junk and return ONLY a JSON object with two lists:

1. "tasks": Important action items the user needs to complete (homework, assignments, deadlines).
   - Include: Canvas assignments, Google Classroom assignments that are due soon or recently posted.
   - Exclude: Old completed assignments, spam, promotional content.
   - Each task has: "title", "source", "due_date" (or null), "url" (or null)

2. "alerts": Important notifications the user should know about NOW.
   - Include: Relevant GroupMe messages (announcements, urgent info), important emails (from real people, school, clubs the user is in).
   - Exclude: Promotional emails (college recruitment mail, LinkedIn spam, marketing), casual GroupMe chatter, duplicate info.
   - Each alert has: "summary", "source", "from"

Return ONLY the raw JSON object. No markdown, no explanation.
Example:
{"tasks": [{"title": "Problem Set 3", "source": "Google Classroom", "due_date": "2026-06-20", "url": null}], "alerts": [{"summary": "Club meeting moved to Thursday", "source": "GroupMe", "from": "Lambert CS Club"}]}
""".strip()


def ask_flash(raw_data: str) -> dict:
    """
    Creates a new Antigravity flash conversation, sends the raw scraped
    data to it, waits for a DONE response, and parses the JSON.
    """
    prompt = f"{SYSTEM_PROMPT}\n\n---\n\nHere is the raw data to process:\n\n{raw_data}"

    logger.info("Spinning up a Gemini Flash AI processor conversation...")
    try:
        result = subprocess.run(
            [AGENTAPI_BIN, "new-conversation", "--model=flash",
             "--title=PersonalAssistantFilter", prompt],
            capture_output=True, text=True, timeout=60
        )
        response = json.loads(result.stdout)
        conv_id = response.get("response", {}).get("conversationId")
        if not conv_id:
            logger.error(f"Failed to create Flash conversation: {response}")
            return {"tasks": [], "alerts": []}
    except Exception as e:
        logger.error(f"Error creating Flash conversation: {e}")
        return {"tasks": [], "alerts": []}

    logger.info(f"Flash conversation created: {conv_id}")

    # Poll the transcript for the DONE response
    transcript_path = os.path.join(TRANSCRIPT_BASE, conv_id,
                                   ".system_generated", "logs", "transcript.jsonl")
    deadline = time.time() + 120  # 2 minute timeout
    last_step = -1

    while time.time() < deadline:
        time.sleep(3)
        if not os.path.exists(transcript_path):
            continue

        with open(transcript_path, "r") as f:
            lines = f.readlines()

        for line in reversed(lines):
            try:
                step = json.loads(line)
            except json.JSONDecodeError:
                continue

            if (step.get("type") == "PLANNER_RESPONSE" and
                    step.get("status") == "DONE" and
                    step.get("step_index", -1) > last_step):

                content = step.get("content", "")
                logger.info(f"Flash AI responded. Parsing JSON...")

                # Strip any accidental markdown fences
                clean = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                try:
                    return json.loads(clean)
                except json.JSONDecodeError:
                    # Try to extract JSON from the response
                    start = clean.find("{")
                    end = clean.rfind("}") + 1
                    if start != -1 and end > start:
                        try:
                            return json.loads(clean[start:end])
                        except Exception:
                            pass
                    logger.error(f"Could not parse JSON from Flash response: {clean[:300]}")
                    return {"tasks": [], "alerts": []}

    logger.error("Flash AI timed out.")
    return {"tasks": [], "alerts": []}


def process_all_sources(canvas_data="", classroom_data="", gmail_data="", groupme_data="") -> dict:
    """Bundle all raw scraped data and send to the AI filter."""
    parts = []
    if canvas_data:
        parts.append(f"=== CANVAS ===\n{canvas_data}")
    if classroom_data:
        parts.append(f"=== GOOGLE CLASSROOM ===\n{classroom_data}")
    if gmail_data:
        parts.append(f"=== GMAIL ===\n{gmail_data}")
    if groupme_data:
        parts.append(f"=== GROUPME ===\n{groupme_data}")

    if not parts:
        return {"tasks": [], "alerts": []}

    raw_data = "\n\n".join(parts)
    return ask_flash(raw_data)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Quick test with fake data
    result = process_all_sources(
        canvas_data="No upcoming assignments found.",
        gmail_data="From: USF Admission <admission@adm.usfca.edu>\nSubject: Put your name on inspiring research, Sanel",
        groupme_data="[Lambert CS Club] Officer meeting MOVED to Thursday 7pm - room 204"
    )
    print(json.dumps(result, indent=2))
