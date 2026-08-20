#!/usr/bin/env bash
# bin/build.sh — build the vocalinux-copr RPMs locally on Fedora (tested on F44)
#
# Usage:
#   bin/build.sh              # build everything (python-pynput, then vocalinux)
#   bin/build.sh vocalinux    # build only vocalinux (+ subpackages)
#   bin/build.sh pynput       # build only python-pynput
#   bin/build.sh --no-check   # skip %check (tests) for faster iterations
#
# Artifacts land in .build/RPMS/noarch/ and .build/SRPMS/.
#
# Build order matters: vocalinux's dynamic BuildRequires include
# python3dist(pynput), which is not in Fedora — the script builds
# python-pynput first and installs it (sudo dnf install of the local RPM)
# before building vocalinux. On COPR this is handled automatically because
# the project's own repo is available to builds.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="$ROOT/.build"
SOURCES="$BUILD/SOURCES"

NO_CHECK=""
TARGETS=()
for arg in "$@"; do
    case "$arg" in
        --no-check) NO_CHECK="--nocheck" ;;
        vocalinux|pynput) TARGETS+=("$arg") ;;
        *) echo "Unknown argument: $arg" >&2; exit 2 ;;
    esac
done
[ ${#TARGETS[@]} -eq 0 ] && TARGETS=(pynput vocalinux)

want() { local t; for t in "${TARGETS[@]}"; do [ "$t" = "$1" ] && return 0; done; return 1; }

echo "==> Checking build tools"
NEED_PKGS=()
for cmd_pkg in "rpmbuild:rpm-build" "spectool:rpmdevtools" "rpmlint:rpmlint"; do
    cmd="${cmd_pkg%%:*}"; pkg="${cmd_pkg##*:}"
    command -v "$cmd" >/dev/null 2>&1 || NEED_PKGS+=("$pkg")
done
# rpm-build needs spectool's companion and the pyproject stack for -bs
rpm -q python3-devel pyproject-rpm-macros >/dev/null 2>&1 || NEED_PKGS+=(python3-devel pyproject-rpm-macros)
rpm -q selinux-policy-devel >/dev/null 2>&1 || NEED_PKGS+=(selinux-policy-devel)
rpm -q systemd >/dev/null 2>&1 || NEED_PKGS+=(systemd)   # provides pkgconfig(systemd) for %selinux_requires
if [ ${#NEED_PKGS[@]} -gt 0 ]; then
    echo "==> Installing missing build tools: ${NEED_PKGS[*]}"
    sudo dnf install -y "${NEED_PKGS[@]}"
fi

mkdir -p "$BUILD"/{SOURCES,SPECS,BUILD,RPMS,SRPMS}

RPMBUILD_DEFS=(
    --define "_topdir $BUILD"
    --define "_sourcedir $SOURCES"
    --define "_specdir $BUILD/SPECS"
    --define "_builddir $BUILD/BUILD"
    --define "_rpmdir $BUILD/RPMS"
    --define "_srcrpmdir $BUILD/SRPMS"
)

# ---------------------------------------------------------------- pynput ---
if want pynput; then
    echo "==> Building python-pynput"
    cp "$ROOT/specs/python-pynput.spec" "$BUILD/SPECS/"
    spectool -g -C "$SOURCES" "$BUILD/SPECS/python-pynput.spec"
    rpmbuild "${RPMBUILD_DEFS[@]}" -bs "$BUILD/SPECS/python-pynput.spec"
    # shellcheck disable=SC2086
    rpmbuild "${RPMBUILD_DEFS[@]}" $NO_CHECK --rebuild "$BUILD"/SRPMS/python-pynput-*.src.rpm
    echo "==> Installing python3-pynput (needed as vocalinux BuildRequires)"
    sudo dnf install -y --allowerasing "$BUILD"/RPMS/noarch/python3-pynput-*.rpm
fi

# ------------------------------------------------------------- vocalinux ---
if want vocalinux; then
    echo "==> Building vocalinux (+ engine-whispercpp, + selinux)"
    cp "$ROOT/specs/vocalinux.spec" "$BUILD/SPECS/"
    # Local sources referenced by the spec (Source1..Source4)
    cp "$ROOT"/selinux/vocalinux.{te,fc,if} "$SOURCES/"
    cp "$ROOT/specs/vocalinux.rpmlintrc" "$SOURCES/"
    spectool -g -C "$SOURCES" "$BUILD/SPECS/vocalinux.spec"
    rpmbuild "${RPMBUILD_DEFS[@]}" -bs "$BUILD/SPECS/vocalinux.spec"
    # shellcheck disable=SC2086
    rpmbuild "${RPMBUILD_DEFS[@]}" $NO_CHECK --rebuild "$BUILD"/SRPMS/vocalinux-0*.src.rpm
fi

# ---------------------------------------------------------------- rpmlint ---
echo "==> rpmlint (filters: specs/vocalinux.rpmlintrc)"
rpmlint -r "$ROOT/specs/vocalinux.rpmlintrc" \
    "$BUILD"/SPECS/*.spec \
    "$BUILD"/RPMS/noarch/*.rpm \
    "$BUILD"/SRPMS/*.src.rpm || true

echo
echo "==> Done. Artifacts:"
ls -1 "$BUILD"/RPMS/noarch/*.rpm "$BUILD"/SRPMS/*.src.rpm 2>/dev/null
echo
echo "Test-install with:"
echo "  sudo dnf install $BUILD/RPMS/noarch/vocalinux-*.rpm \\"
echo "                   $BUILD/RPMS/noarch/python3-pynput-*.rpm"
