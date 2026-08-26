#!/usr/bin/env bash

###############################################################################
# SAIL - Environment Shutdown
#
# Description:
#   Gracefully shuts down the SAIL Raspberry Pi cluster.
#   Kubernetes worker nodes are shut down first. pi-node-1 is shut down last
#   because it hosts the Kubernetes control plane and shared NFS storage.
#
# Usage:
#   chmod +x sail-shutdown.sh
#   ./sail-shutdown.sh
#
###############################################################################

set -u

SSH_USER="sailadmin"

echo
echo "========================================"
echo "SAIL environment shutdown"
echo "========================================"

echo
echo "Shutting down pi-node-3..."
ssh -t "${SSH_USER}@10.0.0.22" "sudo shutdown -h now" || true

echo
echo "Shutting down pi-node-2..."
ssh -t "${SSH_USER}@10.0.0.21" "sudo shutdown -h now" || true

echo
echo "Shutting down pi-node-1..."
ssh -t "${SSH_USER}@10.0.0.20" "sudo shutdown -h now" || true

echo
echo "========================================"
echo "Shutdown commands sent to all nodes"
echo "========================================"
echo "Wait for all systems to fully shut down before disconnecting power."