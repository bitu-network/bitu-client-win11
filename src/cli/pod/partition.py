# file: src/cli/pod/partition.py
import base64
import ctypes
import html
import json
import re
import subprocess
import sys
import threading

MAX_GPT_PARTITIONS = 128  # Windows limit per GPT disk
MAX_MBR_PARTITIONS = 4  # primary partitions on an MBR disk
MAX_PODS = MAX_GPT_PARTITIONS - 2  # minus the pods volume and the auto-created MSR
PODS_VOL_MB = 128  # the `pods` volume only holds empty mount-point folders
# Deliberately does NOT match the `pod_*` label pattern, so this volume is never
# mistaken for a pod.
PODS_LABEL = "pods"


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except (AttributeError, OSError):
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


def run_powershell(command, on_line=None):
    """Run a PowerShell script; call on_line(line) for each stdout line live."""
    # -EncodedCommand: quotes, newlines and $ signs are never mangled by the
    # Windows command line. UTF-8 output keeps non-English locales working.
    prelude = (
        "$ProgressPreference = 'SilentlyContinue'\n"
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
    )
    encoded = base64.b64encode((prelude + command).encode("utf-16-le")).decode("ascii")

    proc = subprocess.Popen(
        ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if proc.stdout is None or proc.stderr is None:
        raise RuntimeError("Could not attach to PowerShell's output streams.")
    stdout, stderr = proc.stdout, proc.stderr

    # Drain stderr on a thread so a full pipe can never block us.
    err_buf = []
    err_thread = threading.Thread(
        target=lambda: err_buf.append(stderr.read()), daemon=True
    )
    err_thread.start()

    lines = []
    for raw in stdout:
        line = raw.rstrip("\r\n")
        lines.append(line)
        if on_line:
            on_line(line)

    proc.wait()
    err_thread.join()

    if proc.returncode != 0:
        error = _clean_clixml("".join(err_buf).strip())
        if not error:
            error = "\n".join(lines).strip()
        raise RuntimeError(f"PowerShell Error: {error}")

    return "\n".join(lines).strip()


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


def get_free_drive_letter_count(disk_number):
    """Drive letters (C-Z) that will be free once the target disk is wiped.
    Returns None if it can't be determined."""
    cmd = f"""
    $target = @(
        Get-Partition -DiskNumber {disk_number} -ErrorAction SilentlyContinue |
        Where-Object {{ [int]$_.DriveLetter -ne 0 }} |
        ForEach-Object {{ [string]$_.DriveLetter }}
    )
    $used = @(
        Get-PSDrive -PSProvider FileSystem |
        ForEach-Object {{ $_.Name }} |
        Where-Object {{ $_.Length -eq 1 -and $target -notcontains $_ }}
    )
    $free = @(
        67..90 | ForEach-Object {{ [string][char]$_ }} |
        Where-Object {{ $used -notcontains $_ }}
    )
    $free.Count
    """
    try:
        return int(run_powershell(cmd).strip().splitlines()[-1])
    except (RuntimeError, OSError, ValueError, IndexError):
        return None


def main():
    if not is_admin():
        print("[-] Error: This script must be run as Administrator to manage physical drives.")
        sys.exit(1)

    print("=== Windows Physical Drive Partition TUI ===")

    try:
        drives = get_physical_drives()
    except (RuntimeError, OSError, ValueError) as e:
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

        n = int(input("Enter number of pods (<n>): ").strip())

        if n < 1:
            print("[-] Number of pods must be at least 1.")
            sys.exit(1)

        if n > MAX_PODS:
            print(
                f"[-] Error: at most {MAX_PODS} pods fit on one disk "
                f"({MAX_GPT_PARTITIONS} partitions minus the pods volume and the reserved partition)."
            )
            sys.exit(1)

        total_size = int(target_drive["Size"])
        min_size_bytes = 100 * 1024 * 1024
        pods_vol_bytes = PODS_VOL_MB * 1024 * 1024

        if (total_size - pods_vol_bytes) / n < min_size_bytes:
            print("[-] Error: Too many pods. Each pod would fall below the safe minimum size.")
            sys.exit(1)

        free_letters = get_free_drive_letter_count(selected_id)
        if free_letters == 0:
            print("[-] Error: no free drive letter is available for the pods volume.")
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
        print(f"    It will be recreated as 1 volume ({PODS_LABEL}, {PODS_VOL_MB} MB, the only drive")
        print(f"    letter) plus {n} NTFS pods, each mounted inside it:")
        print("    " + ", ".join(f"<pods>:\\pod_{i}" for i in range(1, n + 1)))
        print("!" * 75)

        confirm = input(
            "\nType 'YES' to permanently erase this disk and proceed: "
        ).strip()

        if confirm != "YES":
            print("Operation cancelled.")
            sys.exit(0)

        print()

        # Layout: [pods (gets the drive letter)] [pod_1] ... [pod_n]
        # Every pod is its own NTFS volume with NO drive letter, mounted at
        # <pods>:\pod_N. Pods are formatted before being mounted and the Shell
        # Hardware Detection service (AutoPlay) is paused meanwhile, so Windows
        # doesn't pop up "format the disk" prompts or open Explorer windows.
        ps_script = f"""
        $ErrorActionPreference = 'Stop'

        $diskNumber = {selected_id}
        $partitionCount = {n}
        $podsVolMB = {PODS_VOL_MB}
        $podsLabel = '{PODS_LABEL}'
        $sep = [string][char]92

        $disk = Get-Disk -Number $diskNumber

        # Re-check at execution time as a last line of defence.
        if ($disk.IsSystem -or $disk.IsBoot) {{
            throw "Refusing to wipe the system/boot disk."
        }}

        # Leave room for GPT metadata, the auto-created MSR and alignment.
        $overheadMB = 32 + $partitionCount
        $totalMB = [math]::Floor($disk.Size / 1MB)
        $partMB = [math]::Floor(($totalMB - $podsVolMB - $overheadMB) / $partitionCount)

        if ($partMB -lt 100) {{
            throw "The disk is too small for $partitionCount pods."
        }}

        # Pull the volume GUID out of a volume-GUID path (case-insensitive).
        function Get-Guid($text) {{
            if ("$text" -match '[{{]([0-9a-fA-F-]+)[}}]') {{
                return $Matches[1].ToLower()
            }}
            return ''
        }}

        # Ask the mount manager directly what is mounted at a folder
        # (same lookup as: mountvol <folder> /L).
        function Get-MountedGuid($path) {{
            return Get-Guid ((& mountvol.exe ($path + $sep) /L | Out-String))
        }}

        # Pause AutoPlay (Shell Hardware Detection) for the duration.
        $svc = Get-Service -Name ShellHWDetection -ErrorAction SilentlyContinue
        $restartSvc = $false
        if ($svc -and $svc.Status -eq 'Running') {{
            Write-Output "STEP|Pausing AutoPlay to suppress Windows pop-ups"
            Stop-Service -Name ShellHWDetection -Force
            $restartSvc = $true
        }}

        try {{
            Write-Output "STEP|Wiping disk $diskNumber"
            Clear-Disk -Number $diskNumber -RemoveData -RemoveOEM -Confirm:$false

            # Initialise: GPT preferred, MBR fallback (e.g. removable USB sticks)
            $disk = Get-Disk -Number $diskNumber
            if ($disk.PartitionStyle -eq 'RAW') {{
                Write-Output "STEP|Initialising disk as GPT"
                try {{
                    Initialize-Disk -Number $diskNumber -PartitionStyle GPT
                }}
                catch {{
                    $gptError = $_.Exception.Message
                    if ($disk.Size -gt 2TB) {{
                        throw "GPT initialisation failed and the disk is too large for MBR: $gptError"
                    }}
                    if ($partitionCount + 1 -gt {MAX_MBR_PARTITIONS}) {{
                        throw "GPT initialisation failed and MBR allows only {MAX_MBR_PARTITIONS} partitions (pods volume + pods): $gptError"
                    }}
                    Write-Output "WARN|GPT not supported on this disk, using MBR instead"
                    Initialize-Disk -Number $diskNumber -PartitionStyle MBR
                }}
            }}

            # pods volume: the one partition that gets a drive letter.
            Write-Output "STEP|Creating $podsLabel volume"
            $podsPart = New-Partition -DiskNumber $diskNumber -Size ([uint64]($podsVolMB * 1MB))
            Format-Volume -Partition $podsPart -FileSystem NTFS -NewFileSystemLabel $podsLabel -Confirm:$false | Out-Null
            Add-PartitionAccessPath -DiskNumber $diskNumber -PartitionNumber $podsPart.PartitionNumber -AssignDriveLetter
            $podsPart = Get-Partition -DiskNumber $diskNumber -PartitionNumber $podsPart.PartitionNumber
            if ([int]$podsPart.DriveLetter -eq 0) {{
                throw "No free drive letter could be assigned to the pods volume."
            }}
            $podsLetter = [string]$podsPart.DriveLetter
            $podsRoot = $podsLetter + ':' + $sep
            Write-Output "STEP|Pods volume is $($podsLetter):"

            # Pods: create + format (no letter), then mount inside the pods volume.
            for ($i = 1; $i -le $partitionCount; $i++) {{
                Write-Output "STEP|Creating pod_$i ($i of $partitionCount)"

                if ($i -eq $partitionCount) {{
                    $part = New-Partition -DiskNumber $diskNumber -UseMaximumSize
                }}
                else {{
                    $part = New-Partition -DiskNumber $diskNumber -Size ([uint64]($partMB * 1MB))
                }}

                Format-Volume -Partition $part -FileSystem NTFS -NewFileSystemLabel "pod_$i" -Confirm:$false | Out-Null

                $mountPath = $podsRoot + "pod_$i"
                New-Item -ItemType Directory -Path $mountPath | Out-Null
                Add-PartitionAccessPath -DiskNumber $diskNumber -PartitionNumber $part.PartitionNumber -AccessPath $mountPath
            }}

            # Pods must live only inside the pods volume: drop any drive letter Windows
            # may have auto-assigned to them.
            foreach ($p in @(Get-Partition -DiskNumber $diskNumber | Where-Object {{ $_.Type -ne 'Reserved' }})) {{
                if ($p.PartitionNumber -ne $podsPart.PartitionNumber -and [int]$p.DriveLetter -ne 0) {{
                    try {{
                        Remove-PartitionAccessPath -DiskNumber $diskNumber -PartitionNumber $p.PartitionNumber -AccessPath ("$($p.DriveLetter):")
                    }}
                    catch {{
                        Write-Output "WARN|Could not remove the stray drive letter $($p.DriveLetter): from a pod"
                    }}
                }}
            }}

            # Final verification. Mounts are checked against the mount manager
            # itself, not the Storage cmdlets' cached AccessPaths, and retried
            # because volumes and mounts can lag behind for a few seconds.
            Write-Output "STEP|Verifying"
            $expectedParts = $partitionCount + 1
            $partitions = @()
            $pods = @()
            $podsVols = @()
            $failed = @()
            for ($try = 0; $try -lt 10; $try++) {{
                Update-Disk -Number $diskNumber -ErrorAction SilentlyContinue

                # Ignore the automatic Microsoft Reserved partition on GPT disks.
                $partitions = @(
                    Get-Partition -DiskNumber $diskNumber -ErrorAction SilentlyContinue |
                    Where-Object {{ $_.Type -ne 'Reserved' }}
                )
                $volumes = @(
                    $partitions |
                    Get-Volume -ErrorAction SilentlyContinue |
                    Where-Object {{ $_.FileSystem -eq 'NTFS' }}
                )
                $pods = @($volumes | Where-Object {{ $_.FileSystemLabel -like 'pod_*' }})
                $podsVols = @($volumes | Where-Object {{ $_.FileSystemLabel -eq $podsLabel }})

                $failed = @()
                if ($partitions.Count -eq $expectedParts -and $pods.Count -eq $partitionCount -and $podsVols.Count -eq 1) {{
                    foreach ($v in $pods) {{
                        $want = Get-Guid ("$($v.UniqueId) $($v.Path)")
                        $got = Get-MountedGuid ($podsRoot + $v.FileSystemLabel)
                        if ($want -eq '' -or $got -ne $want) {{
                            $failed += $v.FileSystemLabel
                        }}
                    }}
                    if ($failed.Count -eq 0) {{
                        break
                    }}
                }}
                Start-Sleep -Seconds 1
            }}

            if ($partitions.Count -ne $expectedParts) {{
                throw "Verification failed: expected $expectedParts partitions (pods volume + pods), found $($partitions.Count)."
            }}

            if ($pods.Count -ne $partitionCount -or $podsVols.Count -ne 1) {{
                throw "Verification failed: expected 1 pods volume and $partitionCount NTFS pod_* volumes, found $($podsVols.Count) and $($pods.Count)."
            }}

            if ($failed.Count -gt 0) {{
                $firstPath = $podsRoot + $failed[0]
                $raw = (& mountvol.exe ($firstPath + $sep) /L | Out-String).Trim()
                throw "Verification failed: $($failed.Count) of $partitionCount pods are not mounted inside $($podsLetter): (first: $($failed[0]); mountvol says: $raw). The disk itself was partitioned; inspect it with Disk Management."
            }}

            foreach ($p in ($partitions | Sort-Object PartitionNumber)) {{
                $v = $p | Get-Volume -ErrorAction SilentlyContinue
                if ($v.FileSystemLabel -eq $podsLabel) {{
                    $mount = $podsLetter + ':'
                }}
                else {{
                    $mount = $podsRoot + $v.FileSystemLabel
                }}
                Write-Output "RESULT|$($p.PartitionNumber)|$($v.FileSystemLabel)|$($p.Size)|$mount|$($v.FileSystem)"
            }}

            Write-Output "VERIFIED"
        }}
        finally {{
            if ($restartSvc) {{
                Start-Service -Name ShellHWDetection -ErrorAction SilentlyContinue
                Write-Output "STEP|AutoPlay restored"
            }}
        }}
        """

        results = []

        def report(line):
            tag, _, rest = line.partition("|")
            if tag == "STEP":
                print(f"[*] {rest}", flush=True)
            elif tag == "WARN":
                print(f"[!] {rest}", flush=True)
            elif tag == "RESULT":
                fields = rest.split("|")
                if len(fields) >= 5:
                    results.append(fields)

        output = run_powershell(ps_script, on_line=report)

        if "VERIFIED" not in output:
            raise RuntimeError("PowerShell completed without the expected verification result.")

        print("\n[+] Successfully wiped, partitioned, formatted, mounted, and verified the drive!")

        if results:
            print()
            print(f"    {'#':<3} {'Label':<9} {'Size':>11}  {'Mounted at':<14} FS")
            print("    " + "-" * 50)
            for num, label, size, mount, fs in (r[:5] for r in results):
                gb = int(size) / (1024 ** 3)
                print(f"    {num:<3} {label:<9} {gb:>8.2f} GB  {mount:<14} {fs}")

    except ValueError:
        print("[-] Please enter a valid numeric value.")
        sys.exit(1)
    except (RuntimeError, OSError) as e:
        print(f"[-] An error occurred during execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
