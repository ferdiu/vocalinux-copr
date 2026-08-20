%global pypi_name pynput

Name:           python-%{pypi_name}
Version:        1.8.2
Release:        1%{?dist}
Summary:        Monitor and control user input devices

License:        LGPL-3.0-only
URL:            https://github.com/moses-palmer/pynput
Source0:        %{pypi_source}

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros
# importing pynput selects an X backend at import time; the check needs a
# virtual X server
BuildRequires:  xorg-x11-server-Xvfb
BuildRequires:  xorg-x11-drv-dummy
BuildRequires:  python3-evdev
BuildRequires:  python3-xlib
BuildRequires:  python3-six

%global _description %{expand:
pynput allows you to control and monitor input devices: mouse and
keyboard, on X11, Wayland (via Xlib) and other platforms.}

%description %_description

%package -n     python3-%{pypi_name}
Summary:        %{summary}

%description -n python3-%{pypi_name} %_description

%prep
# Upstream setup.py declares build-time setup_requires on lint/docs/upload
# tooling that is irrelevant for building the wheel and not fully packaged
# in Fedora; drop them from the dynamic BuildRequires.
%pyproject_patch_dependency setuptools-lint:ignore
%pyproject_patch_dependency sphinx:ignore
%pyproject_patch_dependency twine:ignore
%autosetup -p1 -n %{pypi_name}-%{version}

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files -l pynput

%check
# %%pyproject_check_import cannot be used: importing pynput opens an X
# connection, so run the import under a virtual framebuffer instead.
xvfb-run -a env PYTHONPATH=%{buildroot}%{python3_sitelib} \
    %{__python3} -c "import pynput, pynput.keyboard, pynput.mouse"

%files -n python3-%{pypi_name} -f %{pyproject_files}
%doc README.rst

%changelog
* Thu Aug 20 2026 ferdiu <ferdiu@users.noreply.github.com> - 1.8.2-1
- Initial COPR package (dependency of vocalinux)
