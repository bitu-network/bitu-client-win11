# file: src/cli/init/foo2.py

def run():
    print("=== Bar Wizard ===")
    print("Step 1: Preparing resources...")
    import time
    time.sleep(1)
    print("Step 2: Processing data...")
    time.sleep(1)
    print("Step 3: Completed!")

if __name__ == "__main__":
    run()
    # print("\n[Press Enter to finish this wizard]")
    # input()
