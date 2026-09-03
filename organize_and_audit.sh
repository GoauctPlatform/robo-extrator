#!/bin/bash

# Folder to store the audit files
AUDIT_BASE_DIR="audit"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
AUDIT_DIR="${AUDIT_BASE_DIR}/run_${TIMESTAMP}"

echo "Creating audit directory: $AUDIT_DIR"
mkdir -p "$AUDIT_DIR"

# Files to move
FILES=(
    "all_parcels_combined.csv"
    "all_parcels_enriched.csv"
    "combined_auctions_data.csv"
    "incomplete_addresses.csv"
    "merge_report.txt"
    "postgres_auction_events.csv"
    "postgres_property_auction_history.csv"
    "postgres_property_details.csv"
)

echo "Moving files to audit directory..."
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$AUDIT_DIR/"
        echo " - Moved: $file"
    else
        echo " - Skipped (not found): $file"
    fi
done

# Reset checkpoint file
CHECKPOINT_FILE="checkpoint_auction_parcels.json"
echo "Resetting $CHECKPOINT_FILE..."
echo '{"done_states": []}' > "$CHECKPOINT_FILE"

# Reset checkpoint do download de calendário
CHECKPOINT_CALENDAR="checkpoint_calendar_download.json"
echo "Resetting $CHECKPOINT_CALENDAR..."
echo '{"done_states": []}' > "$CHECKPOINT_CALENDAR"

# Folders to move
FOLDERS=(
    "parcelfair_auction_parcels_csvs"
    "parcelfair_csv_auctions"
    "split_postgres_csvs"
)

echo "Moving folders to audit directory..."
for folder in "${FOLDERS[@]}"; do
    if [ -d "$folder" ]; then
        mv "$folder" "$AUDIT_DIR/"
        echo " - Moved folder: $folder"
    else
        echo " - Skipped (not found): $folder"
    fi
done

echo "Done! Processes have been audited and checkpoints were reset."
