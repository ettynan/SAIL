#!/usr/bin/env bash

###############################################################################
# SAIL - NFS Client Setup and Verification
#
# Description:
#   Configures NFS client support across the three-node SAIL Kubernetes cluster
#   and verifies that the worker nodes can access the shared NFS storage hosted
#   by pi-node-1.
#
#   The script:
#     1. Installs nfs-common on all three Raspberry Pi nodes.
#     2. Mounts the SAIL NFS share temporarily from pi-node-2.
#     3. Verifies pi-node-2 can write to the shared storage.
#     4. Mounts the same share temporarily from pi-node-3.
#     5. Verifies pi-node-3 can see data written by pi-node-2.
#     6. Verifies pi-node-3 can write to the shared storage.
#     7. Unmounts temporary test mounts when testing is complete.
#
# Requirements:
#   - Run from the SAIL administration MacBook.
#   - SSH access to all three Raspberry Pi nodes must already be configured.
#   - pi-node-1 must already be exporting the NFS share.
#   - The SAIL nodes must be reachable at the addresses defined below.
#
# Usage:
#   chmod +x sail-nfs-client-setup.sh
#   ./sail-nfs-client-setup.sh
#
###############################################################################

set -e

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

SSH_USER="sailadmin"

NODE1="10.0.0.20"
NODE2="10.0.0.21"
NODE3="10.0.0.22"

NFS_SERVER="$NODE1"
NFS_SHARE="/mnt/sail-storage/kubernetes"
TEST_MOUNT="/mnt/sail-nfs-test"


# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

# Display a section heading in the terminal output.
section() {
    echo
    echo "========================================"
    echo "$1"
    echo "========================================"
}


# Install the NFS client utilities on a SAIL node.
install_nfs_client() {
    local node="$1"

    echo "Configuring ${node}..."

    ssh -t "${SSH_USER}@${node}" \
        "sudo apt update && sudo apt install -y nfs-common"

    echo "NFS client configuration completed on ${node}."
}


# -----------------------------------------------------------------------------
# NFS Client Installation
# -----------------------------------------------------------------------------

section "Installing NFS client utilities"

for node in "$NODE1" "$NODE2" "$NODE3"; do
    install_nfs_client "$node"
done


# -----------------------------------------------------------------------------
# pi-node-2 NFS Verification
# -----------------------------------------------------------------------------

section "Testing NFS access from pi-node-2"

ssh -t "${SSH_USER}@${NODE2}" "
    set -e

    # Create a temporary mount point for the NFS verification.
    sudo mkdir -p ${TEST_MOUNT}

    # Mount the SSD-backed NFS share hosted by pi-node-1.
    sudo mount -t nfs -o vers=4.1 \
        ${NFS_SERVER}:${NFS_SHARE} \
        ${TEST_MOUNT}

    echo 'NFS share mounted on pi-node-2.'

    # Display the active mount for verification.
    findmnt ${TEST_MOUNT}

    # Write a file that will later be verified from pi-node-3.
    touch ${TEST_MOUNT}/pi-node-2-test

    if [ ! -f ${TEST_MOUNT}/pi-node-2-test ]; then
        echo 'ERROR: pi-node-2 test file was not created.'
        exit 1
    fi

    echo 'pi-node-2 test file created successfully.'

    ls -l ${TEST_MOUNT}

    # The mount is required only for this verification.
    sudo umount ${TEST_MOUNT}

    echo 'pi-node-2 NFS verification completed successfully.'
"


# -----------------------------------------------------------------------------
# pi-node-3 NFS Verification
# -----------------------------------------------------------------------------

section "Testing NFS access from pi-node-3"

ssh -t "${SSH_USER}@${NODE3}" "
    set -e

    # Create a temporary mount point for the NFS verification.
    sudo mkdir -p ${TEST_MOUNT}

    # Mount the same SSD-backed NFS share.
    sudo mount -t nfs -o vers=4.1 \
        ${NFS_SERVER}:${NFS_SHARE} \
        ${TEST_MOUNT}

    echo 'NFS share mounted on pi-node-3.'

    findmnt ${TEST_MOUNT}

    # Confirm that data written from pi-node-2 is visible from pi-node-3.
    if [ ! -f ${TEST_MOUNT}/pi-node-2-test ]; then
        echo 'ERROR: pi-node-3 cannot see the file created by pi-node-2.'
        exit 1
    fi

    echo 'pi-node-3 can see pi-node-2-test.'

    # Confirm that pi-node-3 can also write to the shared storage.
    touch ${TEST_MOUNT}/pi-node-3-test

    if [ ! -f ${TEST_MOUNT}/pi-node-3-test ]; then
        echo 'ERROR: pi-node-3 test file was not created.'
        exit 1
    fi

    echo 'pi-node-3 test file created successfully.'

    ls -l ${TEST_MOUNT}

    # Remove the temporary mount after verification.
    sudo umount ${TEST_MOUNT}

    echo 'pi-node-3 NFS verification completed successfully.'
"


# -----------------------------------------------------------------------------
# Results
# -----------------------------------------------------------------------------

section "NFS client setup and verification complete"

echo "Verified:"
echo "  - nfs-common installed on all three nodes"
echo "  - pi-node-2 can mount the NFS share"
echo "  - pi-node-2 can write to shared storage"
echo "  - pi-node-3 can mount the NFS share"
echo "  - pi-node-3 can read data written by pi-node-2"
echo "  - pi-node-3 can write to shared storage"