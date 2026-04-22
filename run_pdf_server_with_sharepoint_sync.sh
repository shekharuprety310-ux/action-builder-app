#!/bin/bash
# Saves every "Generate Final PDF" into a folder that syncs to SharePoint via OneDrive.
# 1) In Finder, open your synced SharePoint library, create a folder (e.g. "Variations").
# 2) Drag that folder into Terminal after "export AB_VARIATION_SYNC_DIR=" (with quotes), or paste the path below.

cd "$(dirname "$0")"

# --- EDIT THIS LINE to your real synced folder path (must exist) ---
export AB_VARIATION_SYNC_DIR="${AB_VARIATION_SYNC_DIR:-$HOME/OneDrive-REPLACE_ME/Variations}"

if [[ ! -d "$AB_VARIATION_SYNC_DIR" ]]; then
  echo "Folder not found: $AB_VARIATION_SYNC_DIR"
  echo "Edit AB_VARIATION_SYNC_DIR in this script to a path that exists on your Mac."
  exit 1
fi

echo "SharePoint sync folder: $AB_VARIATION_SYNC_DIR"
echo "Starting PDF server on http://127.0.0.1:8787 ..."
exec python3 variation_pdf_server.py
