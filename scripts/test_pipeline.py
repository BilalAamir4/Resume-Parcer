"""
test_pipeline.py
Quick CLI test — runs the full extraction pipeline on a resume file.

Usage:
    python scripts/test_pipeline.py path/to/resume.pdf
"""

import sys
import json
import os

# Allow imports from the project root regardless of working directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from resume_parser.parser.extractor import ResumeExtractor


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_pipeline.py <path_to_resume>")
        sys.exit(1)

    file_path = sys.argv[1]

    if not os.path.isfile(file_path):
        print(f"Error: File not found — '{file_path}'")
        sys.exit(1)

    print(f"\n[+] Parsing: {file_path}")
    print("-" * 60)

    extractor = ResumeExtractor()
    result = extractor.parse(file_path)

    print(json.dumps(result, indent=2))
    print("-" * 60)

    skill_count = len(result.get("skills", []))
    company_count = len(result.get("companies", []))
    print(f"\n[OK] Extraction complete. Found {skill_count} skills, {company_count} companies.")


if __name__ == "__main__":
    main()
