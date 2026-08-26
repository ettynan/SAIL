#!/usr/bin/env bash

###############################################################################
# SAIL - k3s Prerequisite Configuration
#
# Description:
#   Verifies and configures the Raspberry Pi OS cgroup settings required by
#   k3s across all three SAIL Kubernetes nodes.
#
#   The script:
#     1. Connects to each Raspberry Pi over SSH.
#     2. Checks /boot/firmware/cmdline.txt for the required memory cgroup
#        parameters.
#     3. Adds only parameters that are missing.
#     4. Preserves cmdline.txt as a single logical line.
#     5. Verifies the resulting configuration.
#     6. Reports which nodes require a reboot before k3s installation.
#
# Requirements:
#   - Run from the SAIL administration MacBook.
#   - SSH access to all three Raspberry Pi nodes must already work.
#   - Raspberry Pi OS must already be installed on the nodes.
#
# Usage:
#   chmod +x sail-k3s-prerequisites.sh
#   ./sail-k3s-prerequisites.sh
#
###############################################################################

set -uo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

SSH_USER="sailadmin"

NODES=(
    "10.0.0.20"
    "10.0.0.21"
    "10.0.0.22"
)

CMDLINE_FILE="/boot/firmware/cmdline.txt"

MODIFIED_NODES=()


# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

# Display a section heading in terminal output.
section() {
    echo
    echo "========================================"
    echo "$1"
    echo "========================================"
}


# Verify and configure one Raspberry Pi node in a single SSH session.
configure_node() {
    local node="$1"
    local status

    section "Checking ${node}"

    ssh -t "${SSH_USER}@${node}" \
        "CMDLINE_FILE='${CMDLINE_FILE}' bash -s" <<'REMOTE_SCRIPT'

set -e

REQUIRED_CGROUP_MEMORY="cgroup_memory=1"
REQUIRED_CGROUP_ENABLE="cgroup_enable=memory"

cmdline=$(cat "$CMDLINE_FILE")

echo "Current configuration:"
echo "$cmdline"
echo

missing=()

# Check each required parameter independently.
if [[ " $cmdline " != *" $REQUIRED_CGROUP_MEMORY "* ]]; then
    missing+=("$REQUIRED_CGROUP_MEMORY")
fi

if [[ " $cmdline " != *" $REQUIRED_CGROUP_ENABLE "* ]]; then
    missing+=("$REQUIRED_CGROUP_ENABLE")
fi

# No modification is necessary when both parameters are already present.
if [[ ${#missing[@]} -eq 0 ]]; then
    echo "PASS: Required cgroup parameters are already present."
    exit 0
fi

echo "Missing parameter(s): ${missing[*]}"
echo "Updating $CMDLINE_FILE..."

additions="${missing[*]}"

# Create a backup before changing the boot configuration.
sudo cp "$CMDLINE_FILE" "${CMDLINE_FILE}.sail-backup"

# Append only the missing parameters to the existing command line.
sudo sed -i "1 s|[[:space:]]*$| ${additions}|" "$CMDLINE_FILE"

# Verify that cmdline.txt still contains exactly one logical line.
line_count=$(awk 'END {print NR}' "$CMDLINE_FILE")

if [[ "$line_count" -ne 1 ]]; then
    echo "ERROR: cmdline.txt no longer contains exactly one logical line."
    exit 1
fi

# Verify both required parameters are now present.
updated_cmdline=$(cat "$CMDLINE_FILE")

if [[ " $updated_cmdline " != *" $REQUIRED_CGROUP_MEMORY "* ]] ||
   [[ " $updated_cmdline " != *" $REQUIRED_CGROUP_ENABLE "* ]]; then
    echo "ERROR: Required cgroup parameters were not successfully configured."
    exit 1
fi

echo
echo "PASS: Required cgroup parameters are now configured."
echo "Updated configuration:"
echo "$updated_cmdline"

# Exit code 10 tells the Mac-side script that this node was modified.
exit 10

REMOTE_SCRIPT

    status=$?

    case "$status" in
        0)
            # Node was already configured.
            ;;
        10)
            MODIFIED_NODES+=("$node")
            ;;
        *)
            echo
            echo "ERROR: Prerequisite configuration failed on ${node}."
            exit "$status"
            ;;
    esac
}


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

section "SAIL k3s prerequisite configuration"

for node in "${NODES[@]}"; do
    configure_node "$node"
done


# -----------------------------------------------------------------------------
# Results
# -----------------------------------------------------------------------------

section "k3s prerequisite verification complete"

if [[ ${#MODIFIED_NODES[@]} -eq 0 ]]; then
    echo "All three nodes are configured correctly."
    echo "No reboot is required."
else
    echo "The following node(s) were modified and must be rebooted:"
    printf '  - %s\n' "${MODIFIED_NODES[@]}"

    echo
    echo "Reboot these nodes before installing k3s."
    echo "After they return, run this script again to confirm all nodes pass."
fi