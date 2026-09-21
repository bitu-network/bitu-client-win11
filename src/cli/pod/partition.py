# file: src/cli/pod/partition.py
import base64
import ctypes
import html
import json
import re
import subprocess
import sys


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def _clean_clixml(text):
    """-EncodedCommand makes PowerShell wrap stderr in CLIXML; unwrap it."""
    if not text.startswith("#< CLIXML"):
        return text
    parts = re.findall(r'<S S="Error">(.*?)</S>', text, flags=re.DOTALL)
    msg = "".join(parts)
    msg = (
        msg.replace("_x000D__x000A_", "\n")
        .replace("_x000D_", "")
        .replace("_x000A_", "\n")
    )
    msg = html.unescape(msg).strip()
    # Drop the PowerShell stack-trace noise after the actual message.
    return msg.split("\nAt line:")[0].strip()


def run_powershell(command):
    # Pass the script as -EncodedCommand so quotes, newlines and $ signs are
    # never mangled by the Windows command line. Force UTF-8 output so
    # non-English Windows locales don't break decoding.
    prelude = (
        "$ProgressPreference = 'SilentlyContinue'\n"
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
    )
    encoded = base64.b64encode((prelude + command).encode("utf-16-le")).decode("ascii")

    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        error = _clean_clixml(result.stderr.strip())
        if not error:
            error = result.stdout.strip()
        raise RuntimeError(f"PowerShell Error: {error}")

    return result.stdout.strip()


def get_physical_drives():
    cmd = """
    Get-Disk |
        Sort-Object Number |
        Select-Object Number, FriendlyName, Size, IsSystem, IsBoot,
            @{Name='OperationalStatus'; Expression={ [string]$_.OperationalStatus }} |
        ConvertTo-Json
    """
    output = run_powershell(cmd)
    if not output:
        return []
    data = json.loads(output)
    if isinstance(data, dict):
        data = [data]
    return data


def main():
    if not is_admin():
        print("[-] Error: This script must be run as Administrator to manage physical drives.")
        sys.exit(1)

    print("=== Windows Physical Drive Partition TUI ===")

    try:
        drives = get_physical_drives()
    except Exception as e:
        print(f"[-] Failed to retrieve physical drives: {e}")
        sys.exit(1)

    if not drives:
        print("[-] No physical drives found.")
        sys.exit(1)

    print("\nAvailable Physical Drives:")
    print("-" * 75)

    for d in drives:
        size_gb = int(d["Size"]) / (1024 ** 3)
        flag = "  <-- SYSTEM/BOOT (protected)" if d.get("IsSystem") or d.get("IsBoot") else ""
        print(
            f"[{d['Number']}] {d['FriendlyName']} - "
            f"{size_gb:.2f} GB ({d['OperationalStatus']}){flag}"
        )

    print("-" * 75)

    try:
        selected_id = int(
            input("\nEnter the Disk Number of the drive to partition: ").strip()
        )

        target_drive = next(
            (d for d in drives if int(d["Number"]) == selected_id),
            None
        )

        if not target_drive:
            print("[-] Invalid Disk Number selected.")
            sys.exit(1)

        if target_drive.get("IsSystem") or target_drive.get("IsBoot"):
            print("[-] Refusing to wipe the system/boot disk.")
            sys.exit(1)

        n = int(input("Enter number of partitions (<n>): ").strip())

        if n < 1:
            print("[-] Number of partitions must be at least 1.")
            sys.exit(1)

        total_size = int(target_drive["Size"])
        min_size_bytes = 100 * 1024 * 1024

        if total_size / n < min_size_bytes:
            print("[-] Error: Too many partitions. Each partition would fall below the safe minimum size.")
            sys.exit(1)

        size_gb = total_size / (1024 ** 3)
        name = target_drive["FriendlyName"]
        status = target_drive["OperationalStatus"]

        print("\n" + "!" * 75)
        print("WARNING: THE FOLLOWING PHYSICAL DISK WILL BE COMPLETELY WIPED")
        print("!" * 75)
        print(f"    Disk Number : {selected_id}")
        print(f"    Name        : {name}")
        print(f"    Size        : {size_gb:.2f} GB")
        print(f"    Status      : {status}")
        print()
        print(f"    It will be recreated as {n} NTFS partitions:")
        print("    " + ", ".join(f"pod_{i}" for i in range(1, n + 1)))
        print("!" * 75)

        confirm = input(
            "\nType 'YES' to permanently erase this disk and proceed: "
        ).strip()

        if confirm != "YES":
            print("Operation cancelled.")
            sys.exit(0)

        print(f"[*] Wiping and partitioning Disk {selected_id}...")

        # Uses the Storage cmdlets (not DiskPart): clean -> initialise
        # (GPT, falling back to MBR) -> create + format each partition.
        ps_script = f"""
        $ErrorActionPreference = 'Stop'

        $diskNumber = {selected_id}
        $partitionCount = {n}

        $disk = Get-Disk -Number $diskNumber

        # Re-check at execution time as a last line of defence.
        if ($disk.IsSystem -or $disk.IsBoot) {{
            throw "Refusing to wipe the system/boot disk."
        }}

        # Leave room for GPT metadata, the auto-created MSR and alignment.
        $overheadMB = 32 + $partitionCount
        $totalMB = [math]::Floor($disk.Size / 1MB)
        $partMB = [math]::Floor(($totalMB - $overheadMB) / $partitionCount)

        if ($partMB -lt 100) {{
            throw "The disk is too small for $partitionCount partitions."
        }}

        # 1. Wipe
        Clear-Disk -Number $diskNumber -RemoveData -RemoveOEM -Confirm:$false

        # 2. Initialise: GPT preferred, MBR fallback (e.g. removable USB sticks)
        $disk = Get-Disk -Number $diskNumber
        if ($disk.PartitionStyle -eq 'RAW') {{
            try {{
                Initialize-Disk -Number $diskNumber -PartitionStyle GPT
            }}
            catch {{
                $gptError = $_.Exception.Message
                if ($disk.Size -gt 2TB) {{
                    throw "GPT initialisation failed and the disk is too large for MBR: $gptError"
                }}
                if ($partitionCount -gt 4) {{
                    throw "GPT initialisation failed and MBR supports at most 4 primary partitions: $gptError"
                }}
                Initialize-Disk -Number $diskNumber -PartitionStyle MBR
            }}
        }}

        # 3. Create + format
        for ($i = 1; $i -le $partitionCount; $i++) {{
            if ($i -eq $partitionCount) {{
                $part = New-Partition -DiskNumber $diskNumber -UseMaximumSize -AssignDriveLetter
            }}
            else {{
                $part = New-Partition -DiskNumber $diskNumber -Size ([uint64]($partMB * 1MB)) -AssignDriveLetter
            }}

            Format-Volume -Partition $part -FileSystem NTFS -NewFileSystemLabel "pod_$i" -Confirm:$false | Out-Null
        }}

        # 4. Final verification (retry: volumes can take a few seconds to appear)
        $partitions = @()
        $formatted = @()
        for ($try = 0; $try -lt 10; $try++) {{
            Update-Disk -Number $diskNumber -ErrorAction SilentlyContinue

            # Ignore the automatic Microsoft Reserved partition on GPT disks.
            $partitions = @(
                Get-Partition -DiskNumber $diskNumber -ErrorAction SilentlyContinue |
                Where-Object {{ $_.Type -ne 'Reserved' }}
            )
            $formatted = @(
                $partitions |
                Get-Volume -ErrorAction SilentlyContinue |
                Where-Object {{ $_.FileSystem -eq 'NTFS' -and $_.FileSystemLabel -like 'pod_*' }}
            )

            if ($partitions.Count -eq $partitionCount -and $formatted.Count -eq $partitionCount) {{
                break
            }}
            Start-Sleep -Seconds 1
        }}

        if ($partitions.Count -ne $partitionCount) {{
            throw "Verification failed: expected $partitionCount partitions, found $($partitions.Count)."
        }}

        if ($formatted.Count -ne $partitionCount) {{
            throw "Verification failed: expected $partitionCount NTFS pod_* volumes, found $($formatted.Count)."
        }}

        Write-Output "VERIFIED"
        """

        output = run_powershell(ps_script)

        if "VERIFIED" not in output:
            raise RuntimeError("PowerShell completed without the expected verification result.")

        print("[+] Successfully wiped, partitioned, formatted, and verified the drive!")

    except ValueError:
        print("[-] Please enter a valid numeric value.")
        sys.exit(1)
    except Exception as e:
        print(f"[-] An error occurred during execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
