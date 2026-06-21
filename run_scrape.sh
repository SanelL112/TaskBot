#!/bin/bash
cd /home/sanel/personal-assistant-bot
rm -f offline_archive/export_state.json offline_archive/delta_export.txt mega_index.md source_cache/pdf_exports.txt
python3 scrapers/historical_export.py > export.log 2>&1
python3 scrapers/offline_indexer.py > indexer.log 2>&1
