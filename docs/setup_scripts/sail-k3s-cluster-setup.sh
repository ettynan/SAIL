#!/usr/bin/env bash

###############################################################################
# SAIL - k3s Cluster Setup
#
# Installs and verifies the three-node SAIL k3s cluster.
#
#   pi-node-1  10.0.0.20  k3s server/control plane
#   pi-node-2  10.0.0.21  k3s agent
#   pi-node-3  10.0.0.22  k3s agent
#
# SSH connections are reused during the script to avoid repeated SSH
# password prompts.
###############################################################################

set -euo pipefail

SSH_USER="sailadmin"
SERVER="10.0.0.20"
NODE2="10.0.0.21"
NODE3="10.0.0.22"

# Reuse SSH connections for 10 minutes.
SSH_OPTS="-o ControlMaster=auto -o ControlPersist=10m -o ControlPath=/tmp/sail-ssh-%r@%h:%p"


# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------

cleanup() {
    for node in "$SERVER" "$NODE2" "$NODE3"; do
        ssh $SSH_OPTS -O exit "${SSH_USER}@${node}" 2>/dev/null || true
    done
}

trap cleanup EXIT


# -----------------------------------------------------------------------------
# Establish reusable SSH connections
# -----------------------------------------------------------------------------

echo
echo "========================================"
echo "Opening SSH connections"
echo "========================================"

for node in "$SERVER" "$NODE2" "$NODE3"; do
    echo "Connecting to ${node}..."
    ssh $SSH_OPTS -Nf "${SSH_USER}@${node}"
done


# -----------------------------------------------------------------------------
# Install k3s server on pi-node-1
# -----------------------------------------------------------------------------

echo
echo "========================================"
echo "Installing k3s on pi-node-1"
echo "========================================"

ssh -t $SSH_OPTS "${SSH_USER}@${SERVER}" \
    "curl -sfL https://get.k3s.io | sh -"


# -----------------------------------------------------------------------------
# Wait for control plane
# -----------------------------------------------------------------------------

echo
echo "Waiting for pi-node-1 to become Ready..."

for attempt in {1..36}; do

    if ssh $SSH_OPTS "${SSH_USER}@${SERVER}" \
        "sudo k3s kubectl get node pi-node-1 \
        -o jsonpath='{.status.conditions[?(@.type==\"Ready\")].status}'" \
        2>/dev/null | grep -q True; then

        echo "pi-node-1 is Ready."
        break
    fi

    if [[ "$attempt" -eq 36 ]]; then
        echo "ERROR: pi-node-1 did not become Ready."
        exit 1
    fi

    sleep 5
done


# -----------------------------------------------------------------------------
# Retrieve cluster token
# -----------------------------------------------------------------------------

echo
echo "========================================"
echo "Retrieving cluster join token"
echo "========================================"

K3S_TOKEN=$(
    ssh $SSH_OPTS "${SSH_USER}@${SERVER}" \
        "sudo cat /var/lib/rancher/k3s/server/node-token"
)

if [[ -z "$K3S_TOKEN" ]]; then
    echo "ERROR: Could not retrieve the cluster join token."
    exit 1
fi

echo "Cluster join token retrieved."


# -----------------------------------------------------------------------------
# Install worker nodes
# -----------------------------------------------------------------------------

echo
echo "========================================"
echo "Installing k3s on pi-node-2"
echo "========================================"

ssh -t $SSH_OPTS "${SSH_USER}@${NODE2}" \
    "curl -sfL https://get.k3s.io | \
    K3S_URL='https://${SERVER}:6443' \
    K3S_TOKEN='${K3S_TOKEN}' \
    sh -"


echo
echo "========================================"
echo "Installing k3s on pi-node-3"
echo "========================================"

ssh -t $SSH_OPTS "${SSH_USER}@${NODE3}" \
    "curl -sfL https://get.k3s.io | \
    K3S_URL='https://${SERVER}:6443' \
    K3S_TOKEN='${K3S_TOKEN}' \
    sh -"


# -----------------------------------------------------------------------------
# Verify cluster
# -----------------------------------------------------------------------------

echo
echo "========================================"
echo "Verifying cluster"
echo "========================================"

for attempt in {1..36}; do

    READY_COUNT=$(
        ssh $SSH_OPTS "${SSH_USER}@${SERVER}" \
            "sudo k3s kubectl get nodes --no-headers | \
            awk '\$2 == \"Ready\" {count++} END {print count+0}'"
    )

    if [[ "$READY_COUNT" -eq 3 ]]; then
        break
    fi

    echo "Ready nodes: ${READY_COUNT}/3"

    if [[ "$attempt" -eq 36 ]]; then
        echo "ERROR: Not all nodes became Ready."
        exit 1
    fi

    sleep 5
done


# -----------------------------------------------------------------------------
# Final result
# -----------------------------------------------------------------------------

ssh $SSH_OPTS "${SSH_USER}@${SERVER}" \
    "sudo k3s kubectl get nodes"

echo
echo "========================================"
echo "k3s cluster setup complete"
echo "========================================"

echo "Verified:"
echo "  - k3s server installed on pi-node-1"
echo "  - k3s agent installed on pi-node-2"
echo "  - k3s agent installed on pi-node-3"
echo "  - all three nodes joined the cluster"
echo "  - all three nodes report Ready"