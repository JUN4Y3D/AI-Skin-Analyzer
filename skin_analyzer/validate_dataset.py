"""Command-line entry point for read-only dataset validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .dataset_validation import validate_project, write_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate AI Skin Analyzer dataset files.")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--force", action="store_true", help="allow replacing existing reports")
    args = parser.parse_args(argv)
    project_root = args.project_root.resolve()
    output_dir = (args.output_dir or project_root / "reports").resolve()
    try:
        report = validate_project(project_root)
        json_path, markdown_path = write_report(report, output_dir, args.force)
    except (FileExistsError, OSError, ValueError) as exc:
        print(f"Validation could not complete: {exc}", file=sys.stderr)
        return 2
    print(f"Status: {report['status']}")
    for split, details in report["splits"].items():
        print(f"{split}: {details['csv_rows']} CSV rows, {details['image_files']} image files")
    print("Subject independence: unverified")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
