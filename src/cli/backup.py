# file: src/cli/backup.py
import os
import sys
import shutil
import subprocess
from pathlib import Path

def get_volumes_info():
    cmd = """
    Get-Volume | Where-Object {$_.DriveLetter -ne $null} | ForEach-Object {
        $disk = (Get-Partition -DriveLetter $_.DriveLetter | Get-Disk).Number
        "$($_.DriveLetter)|$($_.FileSystemLabel)|$disk"
    }
    """
    res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
    volumes = {}
    for line in res.stdout.strip().splitlines():
        parts = line.split('|')
        if len(parts) == 3:
            drive, label, disk = parts
            volumes[drive.upper()] = {
                "label": label.strip(),
                "disk": int(disk) if disk.isdigit() else None
            }
    return volumes

def main():
    print("Scanning system volumes...")
    volumes = get_volumes_info()
    
    backup_drive = None
    backup_disk = None
    for drive, info in volumes.items():
        if info["label"].lower() == "backup":
            backup_drive = f"{drive}:\\"
            backup_disk = info["disk"]
            break
            
    if not backup_drive:
        print("Error: No connected drive with the volume label 'backup' was found.")
        sys.exit(1)
        
    print(f"Found backup drive at {backup_drive} (Disk {backup_disk})")
    
    # Look for single-letter folders at the root of the backup drive (e.g., B:\E)
    backup_path = Path(backup_drive)
    targets = []
    
    for item in backup_path.iterdir():
        if item.is_dir() and len(item.name) == 1 and item.name.isalpha():
            target_letter = item.name.upper()
            src_path = Path(f"{target_letter}:\\I")
            
            if target_letter in volumes:
                src_disk = volumes[target_letter]["disk"]
                targets.append((src_path, item, src_disk))
            else:
                print(f"Warning: Marker folder '{target_letter}' found, but drive {target_letter}: is not currently connected.")
                
    if not targets:
        print("No valid drive marker folders found on the backup drive.")
        sys.exit(0)
        
    print(f"Found {len(targets)} active backup target(s).")
    
    for src_path, dest_path, src_disk in targets:
        if not src_path.is_dir():
            print(f"Skipping {src_path}: Source directory does not exist.")
            continue
            
        # Pre-flight physical disk validation check
        if src_disk is not None and backup_disk is not None and src_disk == backup_disk:
            print(f"Error: Aborting {src_path}! Source and backup destination reside on the same physical disk (Disk {src_disk}).")
            continue
            
        dest_path.mkdir(parents=True, exist_ok=True)
        print(f"\n--- Backing up {src_path} -> {dest_path} ---")
        
        inode_map = {}
        source_files = set()
        
        for root, dirs, files in os.walk(src_path):
            rel_path = Path(root).relative_to(src_path)
            dest_dir = dest_path / rel_path
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            for file in files:
                src_file = Path(root) / file
                dst_file = dest_dir / file
                source_files.add(dst_file.resolve())
                
                try:
                    stat = src_file.stat()
                    inode_key = (stat.st_dev, stat.st_ino)
                except Exception:
                    inode_key = None
                
                if inode_key and inode_key in inode_map:
                    existing_dst = inode_map[inode_key]
                    if dst_file.exists():
                        dst_file.unlink()
                    try:
                        os.link(existing_dst, dst_file)
                    except OSError:
                        shutil.copy2(src_file, dst_file)
                else:
                    shutil.copy2(src_file, dst_file)
                    if inode_key:
                        inode_map[inode_key] = dst_file
                        
        # Mirror deletions
        for root, dirs, files in os.walk(dest_path, topdown=False):
            for file in files:
                dst_file = Path(root) / file
                if dst_file.resolve() not in source_files:
                    dst_file.unlink()
            for dir_name in dirs:
                dst_dir = Path(root) / dir_name
                try:
                    dst_dir.rmdir()
                except OSError:
                    pass
                    
        print(f"Completed: {src_path}")

    print("\nAll backups finished successfully.")

if __name__ == "__main__":
    main()