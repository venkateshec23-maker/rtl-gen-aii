"""
package_for_colab.py
Packages training data for Google Colab training.

Usage:
    python scripts/package_for_colab.py

Creates: training_data_export.zip  (~3.9 MB — only the chat-format files)
Upload this zip to Colab alongside the notebook.
"""

import zipfile
from pathlib import Path

EXPORT_DIR = Path("training_data/export")
OUTPUT_ZIP = Path("training_data_export.zip")
FILES = ["rtl_train_chat.jsonl", "rtl_val_chat.jsonl", "rtl_test_chat.jsonl"]

def main():
    if not EXPORT_DIR.exists():
        print(f"ERROR: Export directory not found: {EXPORT_DIR}")
        print("Run Phase 3 first: python dataset_builder.py --export")
        return

    missing = [f for f in FILES if not (EXPORT_DIR / f).exists()]
    if missing:
        print(f"ERROR: Missing files: {missing}")
        return

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in FILES:
            file_path = EXPORT_DIR / f
            zf.write(file_path, arcname=f)
            size_kb = file_path.stat().st_size / 1024
            print(f"  Added {f} ({size_kb:.1f} KB)")

    total_mb = OUTPUT_ZIP.stat().st_size / 1024 / 1024
    print(f"\nCreated: {OUTPUT_ZIP} ({total_mb:.1f} MB)")
    print("\nUpload to Colab:")
    print("  1. Open https://colab.research.google.com/")
    print("  2. File > Upload notebook > upload scripts/train_colab.ipynb")
    print("  3. In Colab, run the upload cell and select this zip")
    print("  4. Or unzip manually: !unzip training_data_export.zip -d training_data/")

if __name__ == "__main__":
    main()
