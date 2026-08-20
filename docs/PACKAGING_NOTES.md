# Packaging notes

## Decisions

- **pywhispercpp is NOT built here**: Fedora officially ships
  `python3-pywhispercpp` (F43+ / Rawhide, x86_64 + aarch64). The
  `vocalinux-engine-whispercpp` subpackage Requires it — no bundling, no
  vendoring.
- **Chroots**: fedora-43-x86_64, fedora-43-aarch64, fedora-rawhide-*.
  F41/F42 are excluded (no pywhispercpp in their repos).
- **Engine variants** use the `vocalinux-engine` virtual provide; future
  `-engine-vosk` / `-engine-whisper` subpackages can coexist for users to
  pick from.
- **SELinux**: custom `vocalinux_t` domain, built with selinux-policy-devel,
  installed **permissive** by default (`semanage permissive -a` in %post) so
  policy bugs never break dictation. Enforcement is opt-in.
- **python-pynput is co-packaged here** because it is a core v0.15.0
  dependency and is not in Fedora. COPR resolves it from the project's own
  repo during the vocalinux build (BuildPynput runs before BuildVocalinux in
  CI).

## v0.15.0-specific quirks (revisit on the next upstream release)

- **License**: v0.15.0 is `GPL-3.0-only`. Upstream's main branch relicensed
  to AGPL-3.0-only — the spec's `License:` field must be updated when the
  next release lands (CI only patches the version!).
- **`%pyproject_patch_dependency vosk:ignore`**: v0.15.0 declares vosk as a
  core dependency, but it is imported lazily (only when the vosk engine is
  selected) and is not in Fedora. Main branch already moved vosk to an
  optional extra — drop this override then.
- **`%pyproject_patch_dependency pydub:ignore`**: pydub is declared in
  v0.15.0 but never imported in `src/` (dead dependency). It is also broken
  on Python 3.13+ (requires an `audioop` shim that is not in Fedora) and
  unpackaged. Dropped deliberately.
- **pywhispercpp >= 1.2** in the engine subpackage matches v0.15.0 upstream
  metadata (main bumped to >=1.5.0; Fedora 43 ships 1.4.0, Rawhide 1.5.0).
- **`Patch0: whispercpp-context-params-guard.patch`** (backport from upstream
  main): v0.15.0 passes `context_params` to `pywhispercpp.Model` whenever a
  Vulkan/CUDA GPU is detected, but Fedora's pywhispercpp 1.4.0 has no such
  `Model.__init__` parameter — it raises AttributeError (uncaught: the
  v0.15.0 fallback only catches TypeError) and the half-constructed Model
  then segfaults on GC. With this patch on 1.4.0, GPU device selection is
  skipped with a warning and dictation works on the default device; on
  pywhispercpp >= 1.5 the guard auto-enables selection. Drop the patch when
  packaging a release that includes the upstream fix.
- **%check deselections**: `test_ibus_engine_core` (needs a running IBus
  daemon) and
  `test_autostart_manager_ext.py::...::test_enable_autostart_permission_error`
  (chmod-based assertions don't apply when building as root). Re-check on
  each version bump whether these still fail in mock.
- **pynput %check** uses xvfb-run instead of `%pyproject_check_import`
  because importing pynput opens an X connection.
- **libayatana-appindicator-gtk3**: explicit Requires is intentional — the
  AyatanaAppIndicator3 typelib ships inside the library package and Fedora
  emits no `typelib()` provide for it.

## rpmlint

Validated to **0 errors / 0 badness** with `rpmlint -r specs/vocalinux.rpmlintrc`.
The filters in `specs/vocalinux.rpmlintrc` document each accepted warning
class (spelling of project names, intentional virtual provide, macro-generated
SELinux scriptlet rm commands, missing man pages, duplicate entry points).

## Local validation recipe (from any distro with docker/podman)

See the history of this repo's CI-era development; roughly:

```bash
docker run --rm -v $PWD:/src:ro -w /src fedora:43 bash -c '
  dnf install -y rpm-build rpmdevtools spectool rpmlint \
    python3-devel pyproject-rpm-macros selinux-policy-devel systemd \
    desktop-file-utils libappstream-glib xorg-x11-server-Xvfb
  # build python-pynput first, then vocalinux; see specs/
'
```

## TODO (future work)

- [ ] `vocalinux-engine-vosk` subpackage (requires packaging `python3-vosk`
      from source — PyPI ships wheels only; check Fedora licensing first).
- [ ] `vocalinux-engine-whisper` subpackage (openai-whisper; heavy torch
      dependency — evaluate Fedora's python3-torch first).
- [ ] On the next upstream release: update `License:` to AGPL-3.0-only and
      drop the `vosk:ignore` override (both are already fixed upstream).
- [ ] Tighten SELinux rules from permissive-mode AVC logs; consider
      enforcing-by-default after several releases with zero denial reports.
- [ ] Offer the spec upstream (VocaHQ/vocalinux#600) for CI-driven releases
      once this COPR has proven stable for a few release cycles.
- [ ] Man pages for `vocalinux` / `vocalinux-gui` (rpmlint
      no-manual-page-for-binary is filtered meanwhile).
