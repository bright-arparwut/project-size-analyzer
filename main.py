from pathlib import Path
import sys
import os

# --- User Configuration ---
PROJECTS_ROOT_DIR = Path("./example_projects") # เปลี่ยนเป็นพาธจริงของคุณ
TARGET_FOLDERS = ["dist", "build", "node_modules"]

def format_bytes(size_bytes: int) -> str:
    """
    แปลงขนาดไฟล์จากไบต์เป็นหน่วยที่มนุษย์อ่านเข้าใจง่าย (KB, MB, GB, etc.)
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
    คำนวณขนาดรวมของไฟล์ทั้งหมดในโฟลเดอร์ที่กำหนด (รวมโฟลเดอร์ย่อย)
    โดยไม่นับ symbolic links เพื่อป้องกันการนับซ้ำและการวนซ้ำไม่รู้จบ
    """
    total_size = 0
    try:
        for item in folder_path.rglob('*'):
            # ตรวจสอบว่าเป็นไฟล์และไม่ใช่ symbolic link
            if item.is_file() and not item.is_symlink():
                try:
                    total_size += item.stat().st_size
                except (OSError, FileNotFoundError) as e:
                    print(f"  ไม่สามารถเข้าถึงไฟล์: {item} ({e})", file=sys.stderr)
    except PermissionError as e:
        print(f"  ไม่มีสิทธิ์เข้าถึง: {folder_path} ({e})", file=sys.stderr)
    return total_size

def find_target_folders_in_project(project_dir: Path, targets: set) -> list[Path]:
    """
    ค้นหาโฟลเดอร์เป้าหมายทั้งหมดภายในไดเรกทอรีโปรเจกต์ที่กำหนด
    """
    found_paths = []
    # ใช้ os.walk เพราะสามารถ "ตัดกิ่ง" การค้นหาได้
    # ซึ่งมีประสิทธิภาพกว่า rglob สำหรับกรณีนี้
    for root, dirs, _ in os.walk(project_dir):
        # สร้างสำเนาของ dirs เพื่อวนลูป และแก้ไขตัวจริง
        current_dirs = list(dirs)
        for d in current_dirs:
            if d in targets:
                found_path = Path(root) / d
                found_paths.append(found_path)
                # เมื่อพบโฟลเดอร์เป้าหมาย ให้หยุดค้นหาลึกลงไปในโฟลเดอร์นั้น
                # โดยการลบออกจากลิสต์ dirs ที่ os.walk จะใช้ต่อไป
                dirs.remove(d)
    return found_paths

def main():
    """
    ฟังก์ชันหลักในการดำเนินงาน: ค้นหาและคำนวณขนาดของโฟลเดอร์เป้าหมาย
    """
    if not PROJECTS_ROOT_DIR.is_dir():
        print(f"[Error] ไดเรกทอรีโปรเจกต์ไม่พบ: {PROJECTS_ROOT_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"กำลังสแกนโปรเจกต์ใน: {PROJECTS_ROOT_DIR}")
    print(f"โฟลเดอร์เป้าหมาย: {', '.join(TARGET_FOLDERS)}")
    print("-" * 50)

    target_set = set(TARGET_FOLDERS)
    all_results = []

    # ค้นหาโปรเจกต์ที่อาจซ้อนกันอยู่หนึ่งระดับ (เช่น YEAR/PROJECT_NAME)
    project_dirs = []

    for project_dir in project_dirs:
        print(f"\n[+] กำลังประมวลผลโปรเจกต์: {project_dir.name}")
        found_folders = find_target_folders_in_project(project_dir, target_set)

        if not found_folders:
            print("  ไม่พบโฟลเดอร์เป้าหมายในโปรเจกต์นี้")
            continue

        for folder_path in found_folders:
            print(f"  -> พบ '{folder_path.name}' ที่: {folder_path.relative_to(PROJECTS_ROOT_DIR)}")
            print(f"     กำลังคำนวณขนาด...")
            size = get_folder_size(folder_path)
            all_results.append({
                "project": project_dir.name,
                "target_name": folder_path.name,
                "full_path": folder_path,
                "size_bytes": size,
                "size_readable": format_bytes(size)
            })

    # แสดงผลสรุป
    print("\n" + "=" * 80)
    print(" สรุปผลการวิเคราะห์ขนาดไดเรกทอรี")
    print("=" * 80)

    if not all_results:
        print("ไม่พบโฟลเดอร์เป้าหมายใดๆ ในทุกโปรเจกต์")
        return

    # จัดเรียงผลลัพธ์ตามขนาดจากมากไปน้อย
    sorted_results = sorted(all_results, key=lambda x: x["size_bytes"], reverse=True)

    # พิมพ์ตารางสรุป
    header = "| {:<20} | {:<15} | {:<20} | {:<50} |".format(
        "Project Root", "Target Folder", "Total Size", "Full Path"
    )
    print(header)
    print("|" + "-" * 22 + "|" + "-" * 17 + "|" + "-" * 22 + "|" + "-" * 52 + "|")

    for result in sorted_results:
        row = "| {:<20} | {:<15} | {:>20} | {:<50} |".format(
            result["project"],
            result["target_name"],
            result["size_readable"],
            str(result["full_path"].relative_to(PROJECTS_ROOT_DIR))
        )
        print(row)
    print("-" * (len(header) - 1))

if __name__ == "__main__":
    main()