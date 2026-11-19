
#!/usr/bin/env bash
set -euo pipefail

# SAIL Grafana SQLite backup
BACKUP_DIR="/Users/user/Desktop/SAIL/backups/grafana"
GRAFANA_DB="/mnt/sail-storage/kubernetes/pvc-5c7727a8-8c82-484b-aa21-14c364b8aef9/grafana.db"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/grafana-$TIMESTAMP.db"

mkdir -p "$BACKUP_DIR"

# Create a consistent SQLite backup on pi-node-1.
ssh sailadmin@10.0.0.20 \
    "sudo sqlite3 '$GRAFANA_DB' '.backup /tmp/grafana-$TIMESTAMP.db'"

# Transfer the backup to the laptop.
ssh sailadmin@10.0.0.20 \
    "sudo cat /tmp/grafana-$TIMESTAMP.db" > "$BACKUP_FILE"

# Remove the temporary backup.
ssh sailadmin@10.0.0.20 \
    "sudo rm /tmp/grafana-$TIMESTAMP.db"

# Verify the copied database.
RESULT=$(sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;")
if [[ "$RESULT" != "ok" ]]; then
    echo "Backup integrity check failed."
    exit 1
fi

# Retain the seven most recent backups.
ls -1t "$BACKUP_DIR"/grafana-*.db | tail -n +8 | while read -r file; do
    rm -- "$file"
done

echo "Grafana backup completed: $BACKUP_FILE"
