# NOTE for future engine variants: the vocalinux-engine virtual provide is the
# extension point. Add -engine-vosk / -engine-whisper subpackages later that
# also "Provides: vocalinux-engine" and let users pick. See
# docs/PACKAGING_NOTES.md (TODO section).

%global upstream_tag v0.15.0
%global gh_owner VocaHQ
%global gh_repo vocalinux

# SELinux policy macros (per fedoraproject.org/wiki/SELinux/IndependentPolicy)
%global selinuxtype targeted
%global modulename vocalinux

Name:           vocalinux
Version:        0.15.0
Release:        1%{?dist}
Summary:        Free, offline voice dictation system for Linux

License:        AGPL-3.0-only
URL:            https://github.com/%{gh_owner}/%{gh_repo}
Source0:        https://github.com/%{gh_owner}/%{gh_repo}/archive/refs/tags/%{upstream_tag}.tar.gz#/%{name}-%{version}.tar.gz
# SELinux policy sources (kept in this packaging repo under selinux/, staged
# into the RPM source dir by CI before rpmbuild -bs)
Source1:        vocalinux.te
Source2:        vocalinux.fc
Source3:        vocalinux.if

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros
# %check dependencies
BuildRequires:  python3-pytest
BuildRequires:  python3-pytest-mock
BuildRequires:  python3-pytest-timeout
# desktop/appstream validation in %check
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
# PyGObject cannot come from pip; require the distro package explicitly
Requires:       python3-gobject
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
Summary:        whisper.cpp speech engine for VocaLinux (via pywhispercpp)
Provides:       vocalinux-engine
Requires:       python3-pywhispercpp >= 1.5.0

%description    engine-whispercpp
Default speech recognition engine for VocaLinux, using the Fedora-provided
python3-pywhispercpp bindings to whisper.cpp.

%package        selinux
Summary:        SELinux policy module for VocaLinux (permissive)
BuildRequires:  selinux-policy-devel
Requires:       selinux-policy-%{selinuxtype}
Requires(post): selinux-policy-%{selinuxtype}
# selinux_requires (not _min) because %post uses semanage
%{?selinux_requires}

%description    selinux
SELinux policy module providing the vocalinux_t confined domain for
VocaLinux. The domain is installed in PERMISSIVE mode by default so a
policy bug can never break dictation; remove the permissive entry with
"semanage permissive -d vocalinux_t" to enforce.

%prep
%autosetup -p1 -n %{gh_repo}-%{upstream_tag}

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
appstream-util validate-relax %{buildroot}%{_datadir}/metainfo/com.vocalinux.Vocalinux.metainfo.xml
%pytest -m "not slow and not integration and not audio"

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
%ghost %verify(not md5 size mode mtime) %{_sharedstatedir}/selinux/%{selinuxtype}/active/modules/200/%{modulename}

%changelog
* Thu Aug 20 2026 ferdiu <ferdiu@users.noreply.github.com> - 0.15.0-1
- Package VocaLinux 0.15.0 for Fedora COPR (engine: whisper.cpp via
  python3-pywhispercpp); optional permissive vocalinux_t SELinux domain
