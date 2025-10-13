#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Translation Update Script for CurvesWB Workbench

This script generates and updates translation files (.ts) for the CurvesWB workbench.
It uses Qt's lupdate and pylupdate tools to extract translatable strings from .ui and .py files.

Requirements:
- lupdate (from Qt)
- pylupdate (from PyQt or PySide)
- lconvert (from Qt)
- lrelease (from Qt)

Usage:
1. Run this script to generate/update TrimFaceDialog.ts:
   python update_translations.py

2. Send the .ts file to translators or upload to Crowdin

3. After receiving translated .ts files, compile them:
   lrelease TrimFaceDialog_de.ts
   lrelease TrimFaceDialog_fr.ts
   etc.

4. The compiled .qm files will be automatically loaded by FreeCAD
"""

import os
import subprocess
import sys

# Paths relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRIMFACE_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "TrimFaceDialog")
TRANSLATIONS_DIR = SCRIPT_DIR

# Files to process
UI_FILES = [os.path.join(TRIMFACE_DIR, "trim_face_dialog.ui")]
PY_FILES = [
    os.path.join(TRIMFACE_DIR, "command.py"),
    os.path.join(TRIMFACE_DIR, "dialog_panel.py"),
    os.path.join(TRIMFACE_DIR, "selection_handlers.py"),
]

def check_tools():
    """Check if required tools are available"""
    tools = {
        "lupdate": ["lupdate", "-version"],
        "pylupdate": ["pylupdate5", "-version"],  # Try pylupdate5 first
        "lconvert": ["lconvert", "-h"],
    }

    available = {}
    for tool_name, cmd in tools.items():
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            available[tool_name] = cmd[0]
            print(f"✓ {tool_name} found: {cmd[0]}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Try alternative for pylupdate
            if tool_name == "pylupdate":
                try:
                    alt_cmd = ["pylupdate6", "-version"]
                    subprocess.run(alt_cmd, capture_output=True, check=True)
                    available[tool_name] = "pylupdate6"
                    print(f"✓ {tool_name} found: pylupdate6")
                    continue
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass
            print(f"✗ {tool_name} not found")
            available[tool_name] = None

    return available

def generate_ts_files(tools):
    """Generate .ts translation files"""
    print("\n" + "="*60)
    print("Generating translation files...")
    print("="*60)

    # Step 1: Extract strings from .ui files
    ui_ts = os.path.join(TRANSLATIONS_DIR, "uifiles.ts")
    if tools["lupdate"] and UI_FILES:
        print(f"\nExtracting strings from UI files...")
        cmd = [tools["lupdate"]] + UI_FILES + ["-ts", ui_ts]
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.returncode != 0:
            print(f"Warning: lupdate returned non-zero: {result.stderr}")

    # Step 2: Extract strings from .py files
    py_ts = os.path.join(TRANSLATIONS_DIR, "pyfiles.ts")
    if tools["pylupdate"] and PY_FILES:
        print(f"\nExtracting strings from Python files...")
        cmd = [tools["pylupdate"]] + PY_FILES + ["-ts", py_ts]
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.returncode != 0:
            print(f"Warning: pylupdate returned non-zero: {result.stderr}")

    # Step 3: Merge UI and Python translations
    output_ts = os.path.join(TRANSLATIONS_DIR, "TrimFaceDialog.ts")
    if tools["lconvert"]:
        print(f"\nMerging translation files...")
        input_files = []
        if os.path.exists(ui_ts):
            input_files.append(ui_ts)
        if os.path.exists(py_ts):
            input_files.append(py_ts)

        if input_files:
            cmd = [tools["lconvert"], "-i"] + input_files + ["-o", output_ts]
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            print(result.stdout)
            if result.returncode == 0:
                print(f"✓ Successfully created {output_ts}")

                # Clean up temporary files
                for temp_file in [ui_ts, py_ts]:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        print(f"  Removed temporary file: {temp_file}")
            else:
                print(f"Error: lconvert failed: {result.stderr}")

    print("\n" + "="*60)
    print("Translation file generation complete!")
    print("="*60)
    print(f"\nNext steps:")
    print(f"1. Review the generated file: {output_ts}")
    print(f"2. Send to translators or upload to translation platform")
    print(f"3. After receiving translated files (e.g., TrimFaceDialog_de.ts):")
    print(f"   lrelease TrimFaceDialog_de.ts")
    print(f"4. The compiled .qm files will be loaded automatically by FreeCAD")

def main():
    print("CurvesWB Translation Update Script")
    print("="*60)

    # Check for required tools
    tools = check_tools()

    missing_tools = [name for name, path in tools.items() if path is None]
    if missing_tools:
        print(f"\n⚠ Warning: Missing tools: {', '.join(missing_tools)}")
        print("\nPlease install Qt Linguist tools:")
        print("  - On Ubuntu/Debian: sudo apt-get install qttools5-dev-tools")
        print("  - On Fedora: sudo dnf install qt5-linguist")
        print("  - On Windows: Install Qt and add bin/ to PATH")
        print("  - Using pip: pip install PyQt5 (includes pylupdate)")

        response = input("\nContinue anyway? [y/N]: ")
        if response.lower() != 'y':
            sys.exit(1)

    # Generate translation files
    generate_ts_files(tools)

if __name__ == "__main__":
    main()
