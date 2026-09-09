# file: src/cli/init/foo3.py

def run():
    print("=== Zar Wizard ===")
    print("Step 1: Initializing...")
    import time
    time.sleep(1)
    print("Step 2: Running main task...")
    time.sleep(1)
    print("Step 3: Finalizing...")
    time.sleep(1)
    print("Step 4: Done!")

if __name__ == "__main__":
    run()
    # print("\n[Press Enter to finish this wizard]")
    # input()
