# file: src/cli/sys_summary.py
import sys
import os
import argparse
import platform
import subprocess
import shutil

def get_cpu_info():
    """Fetches the CPU description, hardware topology, and instant load percentage."""
    cpu_model = "Unknown CPU"
    cores = "Unknown"
    threads = "Unknown"
    cpu_load = "N/A"

    try:
        if platform.system() == "Windows":
            out_model = subprocess.check_output("wmic cpu get name", shell=True).decode().strip().split('\n')
            if len(out_model) > 1:
                cpu_model = out_model[1].strip()
            out_cores = subprocess.check_output("wmic cpu get numberofcores", shell=True).decode().strip().split('\n')
            if len(out_cores) > 1:
                cores = out_cores[1].strip()
            out_threads = subprocess.check_output("wmic cpu get numberoflogicalprocessors", shell=True).decode().strip().split('\n')
            if len(out_threads) > 1:
                threads = out_threads[1].strip()
            out_load = subprocess.check_output("wmic cpu get loadpercentage", shell=True).decode().strip().split('\n')
            if len(out_load) > 1:
                cpu_load = f"{out_load[1].strip()}%"
                
        elif platform.system() == "Linux":
            with open("/proc/cpuinfo", "r") as f:
                lines = f.readlines()
            for line in lines:
                if "model name" in line:
                    cpu_model = line.split(":")[1].strip()
                    break
            try:
                cores = subprocess.check_output("lscpu | grep 'Core(s) per socket:'", shell=True).decode().split(":")[1].strip()
                threads = subprocess.check_output("lscpu | grep 'CPU(s):'", shell=True).decode().split(":")[1].strip()
            except:
                pass
            try:
                cpu_load = f"{os.getloadavg()[0] * 100 / int(threads if threads.isdigit() else 1):.1f}%"
            except:
                pass
            
        elif platform.system() == "Darwin": # macOS
            cpu_model = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode().strip()
            cores = subprocess.check_output(["sysctl", "-n", "hw.physicalcpu"]).decode().strip()
            threads = subprocess.check_output(["sysctl", "-n", "hw.logicalcpu"]).decode().strip()
    except Exception:
        pass

    return {"model": cpu_model, "cores": cores, "threads": threads, "load": cpu_load}

def get_ram_info():
    """Determines physical system memory sizes converted cleanly to Gigabytes."""
    total_gb, avail_gb = 0.0, 0.0
    try:
        if platform.system() == "Windows":
            out_total = subprocess.check_output("wmic computersystem get totalphysicalmemory", shell=True).decode().strip().split('\n')
            if len(out_total) > 1:
                total_gb = int(out_total[1].strip()) / (1024**3)
            out_avail = subprocess.check_output("wmic os get freephysicalmemory", shell=True).decode().strip().split('\n')
            if len(out_avail) > 1:
                avail_gb = int(out_avail[1].strip()) / (1024**2) # Free physical memory returns in KB
        elif platform.system() == "Linux":
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
            for line in lines:
                if "MemTotal" in line:
                    total_gb = int(line.split()[1]) / (1024**2)
                if "MemAvailable" in line:
                    avail_gb = int(line.split()[1]) / (1024**2)
        elif platform.system() == "Darwin":
            out_total = subprocess.check_output(["sysctl", "-n", "hw.memsize"]).decode().strip()
            total_gb = int(out_total) / (1024**3)
    except Exception:
        pass

    used_gb = total_gb - avail_gb
    pct_used = (used_gb / total_gb * 100) if total_gb > 0 else 0
    return {"total": f"{total_gb:.2f} GB", "available": f"{avail_gb:.2f} GB", "used": f"{used_gb:.2f} GB ({pct_used:.1f}%)"}

def main():
    # Setup built-in CLI parsing route
    parser = argparse.ArgumentParser(description="Compact System Capacity Summary Tool")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print extended architecture variables")
    args = parser.parse_args()

    cpu = get_cpu_info()
    ram = get_ram_info()
    try:
        t, u, f = shutil.disk_usage("/")
        disk_str = f"{f / (1024**3):.2f} GB free / {t / (1024**3):.2f} GB"
    except:
        disk_str = "Unknown"

    w = 60
    print("=" * w)
    print(" SYSTEM RESOURCE CAPACITY SUMMARY ".center(w, " "))
    print("=" * w)
    print(f" OS Platform     : {platform.system()} {platform.release()}")
    print(f" CPU Model       : {cpu['model']}")
    print(f" CPU Topology    : {cpu['cores']} Cores / {cpu['threads']} Threads")
    print(f" Current CPU Load: {cpu['load']}")
    print("-" * w)
    print(f" Total RAM       : {ram['total']}")
    print(f" Used / Avail RAM: {ram['used']} / {ram['available']}")
    print(f" Free Disk Space : {disk_str}")
    print("=" * w)

    if args.verbose:
        print(" ARCHITECTURE DETAILS ".center(w, " "))
        print(f" Python Executable: {sys.executable}")
        print(f" Byte Order       : {sys.byteorder}-endian")
        print("=" * w)

    # Smart Workload Classification Rule Engine
    try:
        threads_num = int(cpu['threads'])
        ram_num = float(ram['total'].split()[0])
        print(" WORKLOAD CAPACITY EVALUATION ".center(w, " "))
        print("-" * w)
        if ram_num >= 32 and threads_num >= 12:
            print(" Status: HEAVY WORKLOAD READY")
            print(" Suitability: Intense compiling, massive container clusters, local AI LLMs.")
        elif ram_num >= 16 and threads_num >= 6:
            print(" Status: MODERATE WORKLOAD READY")
            print(" Suitability: Running Docker microservices, IDEs, and active software test suites.")
        else:
            print(" Status: LIGHT WORKLOAD ONLY")
            print(" Suitability: Basic automation scripts, hosting low-traffic sites, simple web tasks.")
    except Exception:
        pass
    print("=" * w)

if __name__ == "__main__":
    main()
