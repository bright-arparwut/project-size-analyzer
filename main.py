from pathlib import Path
import sys
import os
import argparse
import re
import csv
from typing import List, Set, Dict, Any

# --- Default Configuration ---
DEFAULT_TARGET_FOLDERS = [
    "01 Admin",
    "05 Incoming",
    "05 Incomming",
    "06 Outgoing",
    "B. PROJECT DATA",
    "Consultant Drawings",
    "Consultants",
    "Coordinate",
    "Coordination",
    "Correspondence",
    "DATA from consult",
    "Data in",
    "Data out",
    "Email",
    "E-MAIL IN",
    "Email-OUT",
    "File Tranfers",
    "File Transfers",
    "Filetransfer",
    "Filetransfers",
    "For Coordination",
    "FOR FTP",
    "FTP",
    "FTP Upload",
    "In Coming",
    "IN COMING FILE",
    "Incoming",
    "Incoming efiles",
    "Incomming",
    "information for meeting",
    "mail",
    "mail in",
    "mail inbox",
    "mail out",
    "mail sent",
    "Meeting",
    "MEMO",
    "Memorandum",
    "Minutes of meeting",
    "misc Files",
    "Mobile record",
    "Out Going",
    "Outgoing",
    "Project Data",
    "Schedule",
    "TNT",
    "transmital",
    "TRANSMITTAL",
    "Transmittals",
    "UPLOAD",
]

def normalize_name(name: str) -> str:
    """Normalizes a name for comparison by lowercasing and removing non-alphanumeric chars."""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Find and report the size of specified subfolders in a projects directory.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "root_dir",
        type=Path,
        help="The root directory containing the projects to scan."
    )
    parser.add_argument(
        "-t", "--targets",
        nargs='+',
        default=DEFAULT_TARGET_FOLDERS,
        help="A list of target folder names to search for."
    )
    parser.add_argument(
        "--export-csv",
        type=Path,
        help="Export the results to a CSV file at the specified path."
    )
    return parser.parse_args()

def format_bytes(size_bytes: int) -> str:
    """
    Converts a size in bytes to a human-readable format (KB, MB, GB, etc.).
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    for unit in ["KB", "MB", "GB", "TB", "PB"]:
        size_bytes /= 1024
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
    return f"{size_bytes:.2f} PB"

def get_folder_size(folder_path: Path) -> int:
    """
    Calculates the total size of all files in a given folder (including subfolders)
    using os.walk for efficiency. It does not count symbolic links to prevent
    double counting and infinite loops.
    """
    total_size = 0
    try:
        for dirpath, _, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = Path(dirpath) / filename
                # Check if it's a file and not a symbolic link before getting size
                if file_path.is_file() and not file_path.is_symlink():
                    try:
                        total_size += file_path.stat().st_size
                    except (OSError, FileNotFoundError) as e:
                        print(f"  Could not access file: {file_path} ({e})", file=sys.stderr)
    except PermissionError as e:
        # This will catch permission errors for the top-level folder_path
        print(f"  Permission denied to access: {folder_path} ({e})", file=sys.stderr)
    return total_size

def find_target_folders_in_project(project_dir: Path, targets: Set[str]) -> List[Path]:
    """
    Finds all specified target folders within a given project directory.
    The search is case-insensitive, and ignores whitespace and special characters.
    """
    found_paths: List[Path] = []
    # os.walk is used because it allows "pruning" the search,
    # which is more efficient than rglob for this case.
    for root, dirs, _ in os.walk(project_dir):
        # Create a copy of dirs to loop over, while modifying the original
        current_dirs = list(dirs)
        for d in current_dirs:
            if normalize_name(d) in targets:
                found_path = Path(root) / d
                found_paths.append(found_path)
                # Do not prune the directory, so we can find nested target folders.
                # For example, if 'Email' is a target and it's inside 'Data in',
                # we still want to find it.
    return found_paths

def export_to_csv(results: List[Dict[str, Any]], output_file: Path) -> None:
    """Exports the analysis results to a CSV file."""
    if not results:
        print("No results to export.", file=sys.stderr)
        return

    # Make sure the parent directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            # Define the fieldnames from the keys of the first result dictionary
            # This makes it robust if the dictionary structure changes.
            fieldnames = [
                "project",
                "target_name",
                "size_bytes",
                "size_readable",
                "relative_path",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for result in results:
                # We only want to write a subset of the data
                row_data = {key: result[key] for key in fieldnames}
                writer.writerow(row_data)
        print(f"\nSuccessfully exported results to: {output_file}")

    except (IOError, OSError) as e:
        print(f"\n[Error] Failed to write to CSV file: {e}", file=sys.stderr)

def main() -> None:
    """
    Main function to run the operation: find and calculate the size of target folders.
    """
    args = parse_arguments()
    projects_root_dir = args.root_dir
    target_folders = args.targets

    if not projects_root_dir.is_dir():
        print(f"[Error] Project root directory not found: {projects_root_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning projects in: {projects_root_dir}")
    print(f"Target folders: {', '.join(target_folders)} (case-insensitive)")
    print("-" * 50)

    # Convert targets to a normalized set for insensitive matching
    target_set = {normalize_name(t) for t in target_folders}
    all_results: List[Dict[str, Any]] = []

    # Discover project directories directly under the root
    try:
        project_dirs = [d for d in projects_root_dir.iterdir() if d.is_dir()]
    except FileNotFoundError:
        print(f"[Error] Root directory not found: {projects_root_dir}", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"[Error] Permission denied to read directory: {projects_root_dir}", file=sys.stderr)
        sys.exit(1)

    for project_dir in project_dirs:
        print(f"\n[+] Processing project: {project_dir.name}")
        found_folders = find_target_folders_in_project(project_dir, target_set)

        if not found_folders:
            print("  No target folders found in this project.")
            continue

        for folder_path in found_folders:
            relative_path = folder_path.relative_to(projects_root_dir)
            print(f"  -> Found '{folder_path.name}' at: {relative_path}")
            print("     Calculating size...")
            size = get_folder_size(folder_path)
            all_results.append({
                "project": project_dir.name,
                "target_name": folder_path.name,
                "full_path": folder_path,
                "relative_path": relative_path,
                "size_bytes": size,
                "size_readable": format_bytes(size)
            })

    # --- Adjust sizes for nested target folders ---
    # Create a copy of the results to iterate over while modifying the original
    results_copy = list(all_results)
    for parent_result in all_results:
        for child_result in results_copy:
            # If the child is different from the parent and is inside the parent's path
            if parent_result["full_path"] != child_result["full_path"] and \
               child_result["full_path"].is_relative_to(parent_result["full_path"]):

                # Subtract the child's size from the parent's size
                parent_result["size_bytes"] -= child_result["size_bytes"]

    # After adjusting, re-format the human-readable size string
    for result in all_results:
        result["size_readable"] = format_bytes(result["size_bytes"])


    # --- Display Summary ---
    print("\n" + "=" * 80)
    print(" Directory Size Analysis Summary")
    print("=" * 80)

    if not all_results:
        print("No target folders were found in any project.")
        return

    # Sort results by size from largest to smallest
    sorted_results = sorted(all_results, key=lambda x: x["size_bytes"], reverse=True)
    total_size_bytes = sum(r["size_bytes"] for r in sorted_results)

    # Print summary table
    header = f"| {'Project Root':<20} | {'Target Folder':<15} | {'Total Size':>20} | {'Full Path':<50} |"
    print(header)
    print(f"|{'-'*22}|{'-'*17}|{'-'*22}|{'-'*52}|")

    for result in sorted_results:
        row = f"| {result['project']:<20} | {result['target_name']:<15} | {result['size_readable']:>20} | {str(result['relative_path']):<50} |"
        print(row)

    # --- Print Total ---
    print(f"|{'-'*113}|")
    total_readable = format_bytes(total_size_bytes)
    total_line = f"| {'TOTAL':<38} | {total_readable:>20} | {'':<50} |"
    print(total_line)
    print("-" * len(header))

    # --- Export to CSV if requested ---
    if args.export_csv:
        export_to_csv(sorted_results, args.export_csv)


if __name__ == "__main__":
    main()