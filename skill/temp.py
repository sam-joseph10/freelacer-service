import os
import sys
import importlib
import subprocess

# Python standard library modules
STD_LIBS = {
    "os", "sys", "re", "math", "json", "datetime", "logging", "subprocess",
    "threading", "time", "typing", "collections", "functools", "itertools",
    "pathlib", "shutil", "tempfile", "glob", "http", "email", "unittest",
    "importlib", "io", "argparse", "base64", "copy", "inspect", "traceback"
}

def scan_imports():
    imports = set()
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith(".py"):
                try:
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("import ") or line.startswith("from "):
                                parts = line.split()
                                if len(parts) > 1:
                                    mod = parts[1].split(".")[0]
                                    imports.add(mod)
                except Exception:
                    pass
    return imports

def get_installed_version(module_name):
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", module_name],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        return None
    return None

if __name__ == "__main__":
    print("🔍 Scanning project for used external libraries...\n")

    imports = scan_imports()
    external_libs = [m for m in imports if m not in STD_LIBS]

    if not external_libs:
        print("⚠ No external libraries detected.")
        sys.exit(0)

    print(f"📦 External libraries detected: {len(external_libs)}\n")

    found_any = False
    for lib in sorted(external_libs):
        version = get_installed_version(lib)
        if version:
            print(f"{lib}=={version}")
            found_any = True

    if not found_any:
        print("⚠ No real external libraries with versions found.")