import os
import glob
import logging
import asyncio
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def consolidate_memory():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_cache_dir = os.path.join(base_dir, "scrapers", "source_cache")
    
    # Gather raw text
    raw_text = ""
    
    # 1. Read combined_summaries.txt and pdf_exports.txt
    summaries_file = os.path.join(source_cache_dir, "combined_summaries.txt")
    if os.path.exists(summaries_file):
        with open(summaries_file, "r") as f:
            raw_text += "\n--- DAILY SUMMARIES AND NOTES ---\n" + f.read()
            
    pdf_exports_file = os.path.join(source_cache_dir, "pdf_exports.txt")
    if os.path.exists(pdf_exports_file):
        with open(pdf_exports_file, "r") as f:
            raw_text += "\n--- EXPORTED PDFs ---\n" + f.read()
            
    # 2. Read chat_history files
    chat_files = glob.glob(os.path.join(base_dir, "chat_history_*.txt"))
    for cf in chat_files:
        with open(cf, "r") as f:
            raw_text += f"\n--- CHAT HISTORY ({os.path.basename(cf)}) ---\n" + f.read()
            
    if not raw_text.strip():
        logger.info("No raw memory to consolidate tonight.")
        return
        
    prompt = (
        "You are the central Memory Consolidation Engine. It is 2:00 AM. Your task is to process the following raw logs from the day "
        "(including scraped assignments, chat history, and auto-transcribed PDFs) and create a comprehensive, highly detailed index of EVERYTHING that happened.\n\n"
        "Do NOT summarize or omit details. Instead, format your output as a detailed, bulleted index with the following sections:\n"
        "- **Comprehensive Daily Index** (List every single distinct event, conversation, file, concept, and insight found in the logs.)\n"
        "- **Upcoming Deadlines & Tasks** (List all extracted deadlines or action items.)\n"
        "- **Study Topics & Knowledge** (List all academic concepts covered in the notes/assignments.)\n\n"
        "Be completely exhaustive. Include details, dates, and specifics.\n\n"
        f"RAW DATA:\n{raw_text[:30000]}"
    )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2
                    }
                },
                timeout=3600.0
            )
            
        if response.status_code == 200:
            brain = response.json().get("response", "").strip()
        else:
            raise Exception(f"Ollama returned {response.status_code}")
            
    except Exception as e:
        logger.warning(f"Local Llama 3.2 failed to consolidate memory ({e}). Falling back to secure local G1 Flash to protect PII...")
        from ai_processor import call_agy
        brain = call_agy(prompt, timeout=180, model="flash")

    if not brain:
        logger.error("All local models failed to consolidate memory. Aborting to protect PII.")
        return

    try:
            brain_file = os.path.join(base_dir, "curated_brain.md")
            
            import datetime
            today_str = datetime.datetime.now().strftime("%A, %B %d, %Y")
            
            with open(brain_file, "a") as f:
                f.write(f"\n\n# Daily Index: {today_str}\n\n")
                f.write(brain)
                
            # Trigger Deep-Dive Online Researcher
            logger.info("Triggering offline topic researcher...")
            try:
                import subprocess
                subprocess.run(["python3", os.path.join(base_dir, "overnight_researcher.py")], timeout=1800)
            except Exception as e:
                logger.error(f"Overnight researcher failed: {e}")
                
            # 3. Process the Daily PDF Queue (Generate Study Guides)
            logger.info("Processing the nightly PDF queue to generate study guides...")
            try:
                subprocess.run(["python3", os.path.join(base_dir, "scrapers", "nightly_processor.py")], timeout=3600)
            except Exception as e:
                logger.error(f"Nightly processor failed: {e}")
                
            # 4. Massive Historical Indexing
            logger.info("Running massive historical data export...")
            try:
                from scrapers.historical_export import run_all_exports
                run_all_exports()
            except Exception as e:
                logger.error(f"Historical export failed: {e}")
                
            logger.info("Running nightly massive indexer via local 8B model...")
            try:
                # Run it asynchronously
                from scrapers.nightly_indexer import run_indexing
                await run_indexing()
            except Exception as e:
                logger.error(f"Nightly indexer failed: {e}")
                
            logger.info("Daily pipeline complete.")

            # WIPE RAW LOGS
            if os.path.exists(summaries_file):
                os.remove(summaries_file)
            for cf in chat_files:
                os.remove(cf)
                
            logger.info("Memory consolidation complete! Raw logs wiped.")
            
    except Exception as e:
        logger.error(f"Failed to consolidate memory: {e}")

if __name__ == "__main__":
    asyncio.run(consolidate_memory())
