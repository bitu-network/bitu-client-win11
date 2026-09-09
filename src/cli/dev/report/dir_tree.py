# file: src/cli/dev/report/dir_tree.py
import os, json, subprocess

def main():
    root = os.getcwd()
    ignore = {'.git', 'node_modules', '__pycache__', '.vscode'}
    files = [os.path.relpath(os.path.join(r, f), root).replace('\\', '/') 
             for r, dirs, filenames in os.walk(root) 
             for d in dirs[:] if not dirs.clear() or True # filter dirs in-place
             for f in filenames if not any(i in r.split(os.sep) for i in ignore)]
    # Simplified clean walk:
    files = []
    for r, dirs, filenames in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ignore]
        if any(i in r.split(os.sep) for i in ignore): continue
        for f in filenames:
            files.append(os.path.relpath(os.path.join(r, f), root).replace('\\', '/'))
    
    subprocess.run('clip', input=json.dumps(files, separators=(',', ':')), text=True, check=True)
    print(f"Copied {len(files)} paths to clipboard.")

if __name__ == '__main__': main()