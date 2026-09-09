# file: src/cli/init/foo1.py

def run():
    print("=== Foo Wizard ===")
    print("Step 1: Doing something important...")
    # simulate work
    import time
    time.sleep(1)
    print("Step 2: Almost done...")
    time.sleep(1)
    print("Step 3: Finished!")

if __name__ == "__main__":
    run()
    # print("\n[Press Enter to finish this wizard]")
    # input()
