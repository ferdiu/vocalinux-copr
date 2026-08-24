# vocalinux-copr

RPM packaging for [VocaLinux](https://github.com/VocaHQ/vocalinux) — free,
offline voice dictation for Linux — targeting Fedora via
[COPR](https://copr.fedorainfracloud.org/coprs/ferdiu/vocalinux/).

A GitHub Actions workflow runs daily to detect new upstream releases and
trigger fresh COPR builds automatically.

## Packages

| Package | Upstream | Description |
|---------|----------|-------------|
| `vocalinux` | [VocaHQ/vocalinux](https://github.com/VocaHQ/vocalinux) | The dictation app (GTK tray, whisper.cpp default engine) |
| `vocalinux-engine-whispercpp` | same | Default engine, via Fedora's `python3-pywhispercpp` |
| `vocalinux-selinux` | this repo (`selinux/`) | SELinux policy module (`vocalinux_t`, **permissive** by default) |
| `python-pynput` | [PyPI](https://pypi.org/project/pynput/) | Input device monitoring — not in Fedora, built here |

## Install

```bash
sudo dnf copr enable ferdiu/vocalinux
sudo dnf install vocalinux
# vocalinux-engine-whispercpp is pulled in automatically;
# vocalinux-selinux is installed by default via Recommends
```

Supported: **Fedora 43+** (x86_64, aarch64) and Rawhide. Older Fedoras lack
`python3-pywhispercpp`.

## SELinux

`vocalinux-selinux` installs the `vocalinux_t` domain in **permissive** mode:
violations are logged but never blocked, so the policy can never break
dictation. To enforce:

```bash
sudo semanage permissive -d vocalinux_t
```

Report AVC denials (`sudo ausearch -m avc -ts recent`) as issues here.

## COPR build status

[![vocalinux build](https://copr.fedorainfracloud.org/coprs/ferdiu/vocalinux/package/vocalinux/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/ferdiu/vocalinux/package/vocalinux/)
[![python-pynput build](https://copr.fedorainfracloud.org/coprs/ferdiu/vocalinux/package/python-pynput/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/ferdiu/vocalinux/package/python-pynput/)

## Workflow status

[![COPR CI build](https://github.com/ferdiu/vocalinux-copr/actions/workflows/copr-ci.yml/badge.svg)](https://github.com/ferdiu/vocalinux-copr/actions/workflows/copr-ci.yml)

## Tracked versions

| Package | Upstream latest |
|---------|----------------|
| vocalinux | ![vocalinux](https://img.shields.io/badge/vocalinux-0.16.0-blue) |
| python-pynput | ![pynput](https://img.shields.io/badge/pynput-1.8.2-blue) |
