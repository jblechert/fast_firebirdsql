# Windows Installation Guide for fast_firebirdsql

This guide helps you resolve DLL loading issues on Windows.

## The Problem

If you see this error when importing fast_firebirdsql:

```
ImportError: DLL load failed while importing fast_firebirdsql: Das angegebene Modul wurde nicht gefunden.
```

This means Windows cannot find the required DLLs (fbclient.dll and python313.dll).

## Solution 1: Automatic DLL Setup (Recommended)

Run the included setup script to automatically copy the DLLs to the correct location:

```python
import sys
import subprocess

# Run the setup script
result = subprocess.run([sys.executable, "-c", """
import site
from pathlib import Path

# Find the setup script
for site_dir in site.getsitepackages():
    setup_script = Path(site_dir) / 'setup_windows_dlls.py'
    if setup_script.exists():
        exec(setup_script.read_text())
        break
else:
    print('ERROR: setup_windows_dlls.py not found')
"""])
```

Or manually run:

```bash
python -c "import setup_windows_dlls; setup_windows_dlls.setup_windows_dlls()"
```

## Solution 2: Manual DLL Copy

1. Find your Python site-packages directory:
   ```python
   import site
   print(site.getsitepackages())
   ```

2. Navigate to the site-packages directory and find:
   - `fast_firebirdsql/` directory (package)
   - `windows-firebird/` directory (contains DLLs)

3. Copy `fbclient.dll` and `python313.dll` from `windows-firebird/` to `fast_firebirdsql/`

## Solution 3: Add DLLs to PATH

Add the `windows-firebird` directory to your system PATH:

1. Find the full path to `windows-firebird` in your site-packages
2. Add it to your system PATH environment variable
3. Restart your Python session

## Verification

After applying any solution, test the import:

```python
import fast_firebirdsql
print("fast_firebirdsql imported successfully!")

# Test connection (replace with your database details)
conn = fast_firebirdsql.connect(
    host="your_host",
    database="your_database",
    port=3050,
    user="your_user",
    password="your_password"
)
print("Connection successful!")
```

## Troubleshooting

If you still have issues:

1. **Check Firebird installation**: Ensure Firebird client is installed on your system
2. **Check Python version**: The wheel includes python313.dll for Python 3.13
3. **Check architecture**: Ensure you're using 64-bit Python if the wheel is 64-bit
4. **Antivirus software**: Some antivirus programs may block DLL loading

## Technical Details

The fast_firebirdsql package includes:
- `fbclient.dll`: Firebird database client library
- `python313.dll`: Python runtime library for linking
- Automatic DLL discovery and loading logic in `__init__.py`

The package tries multiple strategies to load the DLLs:
1. Direct import (works if DLLs are in the right place)
2. `os.add_dll_directory()` (Python 3.8+)
3. PATH environment variable modification

## Getting Help

If none of these solutions work, please report the issue with:
- Your Python version
- Your Windows version
- The exact error message
- Output of the setup script (if you tried it)
