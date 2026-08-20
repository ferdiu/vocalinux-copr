# NOTE for future engine variants: the vocalinux-engine virtual provide is the
# extension point. Add -engine-vosk / -engine-whisper subpackages later that
# also "Provides: vocalinux-engine" and let users pick. See
# docs/PACKAGING_NOTES.md (TODO section).

%global upstream_tag v0.15.0
# tag without the leading v (tarball top-level dir is repo-tag_version)
%global tag_version 0.15.0
%global gh_owner VocaHQ
%global gh_repo vocalinux

# SELinux policy macros (per fedoraproject.org/wiki/SELinux/IndependentPolicy)
%global selinuxtype targeted
%global modulename vocalinux

Name:           vocalinux
Version:        0.15.0
Release:        1%{?dist}
Summary:        Free, offline voice dictation system for Linux

# Upstream relicensed GPL-3.0 -> AGPL-3.0 after v0.15.0 (main branch is
# AGPL-3.0-only). This field MUST match the packaged release's LICENSE:
# revisit on the next upstream release bump.
License:        GPL-3.0-only
URL:            https://github.com/%{gh_owner}/%{gh_repo}
Source0:        https://github.com/%{gh_owner}/%{gh_repo}/archive/refs/tags/%{upstream_tag}.tar.gz#/%{name}-%{version}.tar.gz
# SELinux policy sources (kept in this packaging repo under selinux/, staged
# into the RPM source dir by CI before rpmbuild -bs)
Source1:        vocalinux.te
Source2:        vocalinux.fc
Source3:        vocalinux.if
Source4:        vocalinux.rpmlintrc

# Backport from upstream main: v0.15.0 passes context_params (GPU device
# selection) to pywhispercpp unconditionally when Vulkan/CUDA is detected.
# Fedora's pywhispercpp 1.4.0 has no context_params in Model.__init__, which
# raises AttributeError (the v0.15.0 fallback only catches TypeError) and the
# partially constructed Model then segfaults on GC. The patch guards the
# kwarg behind a signature inspection and catches AttributeError too.
# DROP THIS PATCH when packaging a release that includes the upstream fix.
Patch0:         whispercpp-context-params-guard.patch

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros
# dependencies for the check section
BuildRequires:  python3-pytest
BuildRequires:  python3-pytest-mock
BuildRequires:  python3-pytest-timeout
# desktop/appstream validation in the check section
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib

# Non-Python runtime tools used by text_injection and the tray UI
Requires:       xdotool
Requires:       wtype
Requires:       wl-clipboard
Requires:       xclip
Requires:       xsel
Requires:       gtk3
Requires:       libayatana-appindicator-gtk3
# Engine selection (virtual provide; see header note)
Requires:       vocalinux-engine
# Optional confined domain; works unconfined without it
Recommends:     %{name}-selinux = %{version}-%{release}

%description
VocaLinux is a seamless, offline voice dictation system for Linux.
It uses whisper.cpp (via pywhispercpp) for local speech recognition,
integrates with the system tray (AppIndicator), and injects dictated
text into X11 and Wayland applications.

%package        engine-whispercpp
Summary:        Whisper.cpp speech engine for VocaLinux (via pywhispercpp)
Provides:       vocalinux-engine
# v0.15.0 upstream requires pywhispercpp>=1.2 (main branch bumped to >=1.5;
# Fedora 43 ships 1.4.0, Rawhide 1.5.0 — match the packaged release)
Requires:       python3-pywhispercpp >= 1.2

%description    engine-whispercpp
Default speech recognition engine for VocaLinux, using the Fedora-provided
python3-pywhispercpp bindings to whisper.cpp.

%package        selinux
Summary:        SELinux policy module for VocaLinux (permissive)
# selinux_requires (not _min) because the post scriptlet uses semanage; it
# also provides BuildRequires: selinux-policy-devel/pkgconfig(systemd) and
# the Requires/Requires(post) on selinux-policy packages.
%{?selinux_requires}

%description    selinux
SELinux policy module providing the vocalinux_t confined domain for
VocaLinux. The domain is installed in PERMISSIVE mode by default so a
policy bug can never break dictation; remove the permissive entry with
"semanage permissive -d vocalinux_t" to enforce.

%prep
# v0.15.0 declares vosk as a CORE dependency, but vosk is not in Fedora and
# the code imports it lazily (only when the vosk engine is selected). Our
# package ships the whispercpp engine, so drop the dep from both the dynamic
# BuildRequires and the generated runtime Requires. Future releases (main
# branch) have already moved vosk to an optional extra — drop this override
# when packaging a release that includes that change.
%pyproject_patch_dependency vosk:ignore
# pydub is declared in v0.15.0 but never imported anywhere in src/ (dead
# dependency); it is also unpackaged in Fedora and broken on Python 3.13+
# (needs an audioop shim). Drop it.
%pyproject_patch_dependency pydub:ignore
%autosetup -p1 -n %{gh_repo}-%{tag_version}

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

# Build the SELinux policy module from the policy sources
mkdir -p selinux-build && cd selinux-build
cp %{SOURCE1} %{SOURCE2} %{SOURCE3} .
make -f %{_datadir}/selinux/devel/Makefile vocalinux.pp
bzip2 -9 vocalinux.pp
cd ..

%install
%pyproject_install
%pyproject_save_files -l vocalinux
# Upstream ships main.py with a shebang but mode 0644; make it executable
chmod 0755 %{buildroot}%{python3_sitelib}/vocalinux/main.py

# Desktop file and AppStream metainfo (from packaging/flatpak/ in the tarball)
install -Dm0644 packaging/flatpak/com.vocalinux.Vocalinux.desktop \
    %{buildroot}%{_datadir}/applications/com.vocalinux.Vocalinux.desktop
install -Dm0644 packaging/flatpak/com.vocalinux.Vocalinux.metainfo.xml \
    %{buildroot}%{_datadir}/metainfo/com.vocalinux.Vocalinux.metainfo.xml

# Application icon (hicolor, SVG)
install -Dm0644 resources/icons/scalable/vocalinux.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/com.vocalinux.Vocalinux.svg

# SELinux policy module + interfaces
install -Dm0644 selinux-build/vocalinux.pp.bz2 \
    %{buildroot}%{_datadir}/selinux/packages/%{selinuxtype}/%{modulename}.pp.bz2
install -Dm0644 %{SOURCE3} \
    %{buildroot}%{_datadir}/selinux/devel/include/distributed/%{modulename}.if

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/com.vocalinux.Vocalinux.desktop
appstream-util validate-relax --nonet %{buildroot}%{_datadir}/metainfo/com.vocalinux.Vocalinux.metainfo.xml
# Deselected tests are environment-specific, not product defects:
#  - test_ibus_engine_core: needs a running IBus daemon (no ibus in mock)
#  - test_enable_autostart_permission_error: asserts chmod-based permission
#    failures, which do not apply when the build runs as root
%pytest -m "not slow and not integration and not audio" \
    -k "not test_ibus_engine_core" \
    --deselect tests/test_autostart_manager_ext.py::TestAutostartManagerExtra::test_enable_autostart_permission_error

%files -f %{pyproject_files}
%doc README.md
%{_bindir}/vocalinux
%{_bindir}/vocalinux-gui
%{_datadir}/applications/com.vocalinux.Vocalinux.desktop
%{_datadir}/metainfo/com.vocalinux.Vocalinux.metainfo.xml
%{_datadir}/icons/hicolor/scalable/apps/com.vocalinux.Vocalinux.svg

%files engine-whispercpp
# Virtual-provide-only subpackage; no files.

%post selinux
%selinux_modules_install -s %{selinuxtype} %{_datadir}/selinux/packages/%{selinuxtype}/%{modulename}.pp.bz2
# Apply file contexts for the installed entry points
if selinuxenabled 2>/dev/null; then
    restorecon -R %{_bindir}/vocalinux %{_bindir}/vocalinux-gui 2>/dev/null || true
    # Install the domain as permissive by default so policy bugs never
    # break dictation; users opt into enforcement explicitly.
    semanage permissive -a vocalinux_t 2>/dev/null || true
fi

%postun selinux
if [ $1 -eq 0 ]; then
    semanage permissive -d vocalinux_t 2>/dev/null || true
    %selinux_modules_uninstall -s %{selinuxtype} %{modulename}
fi

%files selinux
%{_datadir}/selinux/packages/%{selinuxtype}/%{modulename}.pp.*
%{_datadir}/selinux/devel/include/distributed/%{modulename}.if
%ghost %attr(0644,root,root) %verify(not md5 size mode mtime) %{_sharedstatedir}/selinux/%{selinuxtype}/active/modules/200/%{modulename}

%changelog
* Thu Aug 20 2026 ferdiu <ferdiu@users.noreply.github.com> - 0.15.0-1
- Package VocaLinux 0.15.0 for Fedora COPR (engine: whisper.cpp via
  python3-pywhispercpp); optional permissive vocalinux_t SELinux domain
