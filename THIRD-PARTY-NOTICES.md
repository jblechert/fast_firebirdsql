# Third-Party Notices

fast_firebirdsql redistributes the following third-party binaries in its
wheels. They are not covered by this project's MIT license.

## Firebird client library

- Files: `windows-firebird/fbclient.dll` (win_amd64 wheel),
  `fast_firebirdsql.libs/libfbclient-*.so.2` (manylinux wheel)
- Copyright: Firebird Project, https://firebirdsql.org
- License: Initial Developer's Public License Version 1.0 (IDPL) and
  InterBase Public License Version 1.0 (IPL)
- License texts: https://firebirdsql.org/en/licensing/
- Source code: https://github.com/FirebirdSQL/firebird

## Python runtime library

- File: `windows-firebird/python313.dll` (win_amd64 wheel)
- Copyright: Python Software Foundation, https://www.python.org
- License: PSF License Agreement for Python (PSF-2.0)
- License text: https://docs.python.org/3/license.html

## LibTomMath

- File: `fast_firebirdsql.libs/libtommath-*.so.1` (manylinux wheel,
  dependency of the Firebird client library)
- Project: https://www.libtom.net
- License: The Unlicense (public domain equivalent)

## Rust crate dependencies

The compiled extension module statically includes Rust crates, most
notably [rsfbclient](https://crates.io/crates/rsfbclient) (MIT) and
[PyO3](https://crates.io/crates/pyo3) (MIT OR Apache-2.0). A complete
machine-readable inventory ships inside each wheel as a CycloneDX SBOM
(`*.dist-info/sboms/`).
