import pytest
from main import normalize_name, find_target_folders_in_project, get_folder_size, main
from pathlib import Path
import os
import sys

@pytest.mark.parametrize("input_name, expected_output", [
    ("01 Admin", "01admin"),
    ("05 Incoming", "05incoming"),
    ("B. PROJECT DATA", "bprojectdata"),
    ("E-MAIL IN", "emailin"),
    ("File Transfers", "filetransfers"),
    ("FTP Upload", "ftpupload"),
    ("mail-inbox", "mailinbox"),
    ("Minutes of meeting", "minutesofmeeting"),
    ("Schedule", "schedule"),
    ("TRANSMITTAL", "transmittal"),
    ("nochange", "nochange"),
    ("With--Dashes", "withdashes"),
    ("with_underscores", "withunderscores"),
    ("A Folder With Spaces", "afolderwithspaces"),
    ("folder123", "folder123"),
    ("!@#$%^&*()", ""),
])
def test_normalize_name(input_name, expected_output):
    """Tests the normalize_name function with various inputs."""
    assert normalize_name(input_name) == expected_output

def test_find_target_folders_in_project(tmp_path: Path):
    """Tests the find_target_folders_in_project function."""
    # Create a mock project structure
    project_dir = tmp_path / "project1"
    project_dir.mkdir()
    (project_dir / "src").mkdir()
    (project_dir / "Data in").mkdir()  # Should be found
    (project_dir / "docs").mkdir()
    (project_dir / "docs" / "E-MAIL-OUT").mkdir()  # Should be found
    (project_dir / "some_other_folder").mkdir()
    (project_dir / "FOR FTP").mkdir() # Should be found from a different target name

    # Define the targets, already normalized as they would be in main()
    targets = {"datain", "emailout", "forftp"}

    # Run the function
    found_folders = find_target_folders_in_project(project_dir, targets)

    # Assertions
    assert len(found_folders) == 3

    # Use a set of relative paths for easier comparison
    found_paths_relative = {str(p.relative_to(project_dir)) for p in found_folders}
    expected_paths = {
        "Data in",
        os.path.join("docs", "E-MAIL-OUT"),
        "FOR FTP"
    }
    assert found_paths_relative == expected_paths

def test_get_folder_size(tmp_path: Path):
    """Tests the get_folder_size function."""
    folder = tmp_path / "test_folder"
    folder.mkdir()
    (folder / "file1.txt").write_text("12345")
    (folder / "file2.txt").write_text("1234567890")
    subfolder = folder / "sub"
    subfolder.mkdir()
    (subfolder / "file3.txt").write_text("12345")

    # Expected size = 5 + 10 + 5 = 20 bytes
    expected_size = 20
    calculated_size = get_folder_size(folder)

    assert calculated_size == expected_size

def test_main_integration(tmp_path: Path, monkeypatch, capsys):
    """Integration test for the main function."""
    # Create a mock project structure
    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    project1 = projects_root / "project1"
    project1.mkdir()
    (project1 / "node_modules").mkdir()
    (project1 / "node_modules" / "file.js").write_text("a" * 100)
    project2 = projects_root / "project2"
    project2.mkdir()
    (project2 / "build").mkdir()
    (project2 / "build" / "app.exe").write_text("b" * 2000) # 2000 bytes -> 1.95 KB
    (project2 / "dist").mkdir() # empty folder

    # Mock sys.argv
    monkeypatch.setattr(sys, "argv", ["main.py", str(projects_root), "-t", "node_modules", "build", "dist"])

    main()

    captured = capsys.readouterr()
    output = captured.out

    # Assertions on the output
    assert "Scanning projects in" in output
    assert "Target folders: node_modules, build, dist" in output
    assert "Processing project: project1" in output
    assert "Found 'node_modules'" in output
    assert "100 B" in output
    assert "Processing project: project2" in output
    assert "Found 'build'" in output
    assert "1.95 KB" in output
    assert "Found 'dist'" in output
    assert "0 B" in output
    assert "Directory Size Analysis Summary" in output
    assert "TOTAL" in output
    assert "2.05 KB" in output # 2100 bytes total

def test_nested_target_folders_size_calculation(tmp_path: Path, monkeypatch, capsys):
    """
    Tests that the script correctly calculates the size of nested target folders,
    ensuring the parent folder's size excludes the nested one's.
    """
    # --- Setup ---
    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    project_nested = projects_root / "project_nested"
    project_nested.mkdir()

    # Create nested structure: "Data in" contains "Email"
    data_in_dir = project_nested / "Data in"
    data_in_dir.mkdir()
    (data_in_dir / "some_file.txt").write_text("a" * 1024)  # 1 KB

    email_dir = data_in_dir / "Email"
    email_dir.mkdir()
    (email_dir / "email_content.txt").write_text("b" * 512) # 0.5 KB

    # --- Execution ---
    # Mock sys.argv to run the script on our test directory
    monkeypatch.setattr(sys, "argv", ["main.py", str(projects_root), "-t", "Data in", "Email"])
    main()

    # --- Assertion ---
    captured = capsys.readouterr()
    output = captured.out

    # The size of "Data in" should be 1.00 KB (excluding "Email")
    # The size of "Email" should be 512 B
    # Total should be 1.50 KB

    # Let's check for the specific lines in the summary table
    # We use regex to be flexible with whitespace
    import re
    data_in_line_found = re.search(r"\|\s*project_nested\s*\|\s*Data in\s*\|\s*1.00 KB\s*\|", output)
    email_line_found = re.search(r"\|\s*project_nested\s*\|\s*Email\s*\|\s*512 B\s*\|", output)
    total_line_found = re.search(r"\|\s*TOTAL\s*\|\s*1.50 KB\s*\|", output)

    assert data_in_line_found, "The output for 'Data in' should show 1.00 KB"
    assert email_line_found, "The output for 'Email' should show 512 B"
    assert total_line_found, "The total size should be correctly calculated as 1.50 KB"
