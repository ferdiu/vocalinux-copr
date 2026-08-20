#!/usr/bin/env bash
# bin/build-container.sh — build the vocalinux-copr RPMs inside a Fedora 44
# container, without touching the host system.
#
# Runtime autodetection order: podman -> docker -> error.
#
# Usage (arguments are forwarded to bin/build.sh):
#   bin/build-container.sh              # build everything
#   bin/build-container.sh vocalinux    # build only vocalinux (+ subpackages)
#   bin/build-container.sh pynput       # build only python-pynput
#   bin/build-container.sh --no-check   # skip %check for faster iterations
#
# Artifacts land in .build/ (same as bin/build.sh), owned by root — the
# script fixes ownership back to the invoking user afterwards.
#
# Note: the .build tree is shared with bin/build.sh; if you switch between
# host and container builds, delete .build first (or use sudo) to avoid
# permission issues.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="fedora:44"

# -------------------------------------------------------- runtime detect ---
RUNTIME=""
if command -v podman >/dev/null 2>&1; then
    RUNTIME="podman"
elif command -v docker >/dev/null 2>&1; then
    RUNTIME="docker"
else
    echo "ERROR: neither podman nor docker found." >&2
    echo "Install one with: sudo dnf install podman" >&2
    exit 1
fi
echo "==> Using container runtime: $RUNTIME (image: $IMAGE)"

# ------------------------------------------------------------- run build ---
# :Z relabels the bind mount so the container can read/write it on SELinux
# systems. The repo is mounted read-write because bin/build.sh writes its
# rpmbuild tree to .build/.
# --userns=keep-id maps the invoking host user into the container with the
# same uid, so the cleanup chown below produces host files owned by you
# (https://docs.podman.io/en/v4.6.1/markdown/options/userns.container.html).
# keep-id defaults the container process to the invoking user, so pin
# --user 0:0: the build needs root for dnf installs.
"$RUNTIME" run --rm \
    --userns=keep-id \
    --user 0:0 \
    -v "$ROOT:/src:Z" \
    -w /src \
    "$IMAGE" \
    bash bin/build.sh "$@"

# ------------------------------------------------- fix .build ownership ----
if [ -d "$ROOT/.build" ]; then
    # Files were written by container-root; with keep-id, chowning to the
    # invoking uid inside the container maps 1:1 to your host account.
    echo "==> Fixing .build ownership back to uid $(id -u)"
    "$RUNTIME" run --rm \
        --userns=keep-id \
        --user 0:0 \
        -v "$ROOT/.build:/out:Z" \
        --entrypoint /bin/chown \
        "$IMAGE" \
        -R "$(id -u):$(id -g)" /out
fi

echo
echo "==> Container build done. Artifacts:"
ls -1 "$ROOT"/.build/RPMS/noarch/*.rpm "$ROOT"/.build/SRPMS/*.src.rpm 2>/dev/null || true
