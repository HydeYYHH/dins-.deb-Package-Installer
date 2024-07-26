#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import argparse
import os
import re
import subprocess
import sys
import argcomplete

CACHE_PATH = os.path.expanduser("~/.cache/dins")
CONF_PATH = os.path.expanduser("~/.config/dins")

def check_usr():
    """Check if the script is run as root, which should be avoided."""
    if os.geteuid() == 0:
        print("Avoid running dins as root/sudo.")
        sys.exit(1)

def check_dir():
    """Create cache and config directories if they don't exist."""
    os.makedirs(CACHE_PATH, exist_ok=True)
    os.makedirs(CONF_PATH, exist_ok=True)

def clean_cache():
    """Remove the cache directory."""
    try:
        remove(CACHE_PATH, privilege=1, mute_log=True)
    except FileNotFoundError:
        pass

def move(src, dest, privilege: int = 0):
    """Move a file or directory, optionally using sudo."""
    print(f"Moving from {src} to {dest}")
    cmd = ['sudo', 'mv', '-f', src, dest] if privilege == 0 else ['mv', src, dest]
    subprocess.run(cmd, check=True, capture_output=True)

def remove(path, privilege: int = 0, mute_log: bool = False):
    """Remove a file or directory, optionally using sudo."""
    if not mute_log:
        print(f"Removing {path}")
    cmd = ['sudo', 'rm', '-r', path] if privilege == 0 else ['rm', '-r', path]
    subprocess.run(cmd, capture_output=True)

def mkdir(path, privilege: int = 0):
    """Create a directory, optionally using sudo."""
    print(f"Creating directory {path}")
    cmd = ['sudo', 'mkdir', '--parent', path] if privilege == 0 else ['mkdir', '--parent', path]
    subprocess.run(cmd, check=True, capture_output=True)

def get_paths(dirs, paths, dir_path, base_path):
    """Recursively collect directories and file paths."""
    for entry in os.listdir(dir_path):
        full_path = os.path.join(dir_path, entry)
        relative_path = os.path.relpath(full_path, base_path)
        if os.path.isfile(full_path):
            paths.append(relative_path)
        elif os.path.isdir(full_path):
            dirs.append(relative_path)
            get_paths(dirs, paths, full_path, base_path)
    return dirs, paths

def parse_package(package_path):
    """Parse the control file of a package and return package information."""
    package_info = {}
    control_file = os.path.join(CONF_PATH, os.path.basename(package_path), "control")
    print(f"Parsing package control file: {control_file}")
    try:
        with open(control_file, encoding='utf-8') as file:
            data = file.read()
    except FileNotFoundError:
        print(f"Control file not found at {control_file}")
        sys.exit(1)

    pattern = r'^(Package|Version|Depends|Recommends|Priority|Architecture|Maintainer|Homepage|Description):\s*(.*)$'
    matches = re.findall(pattern, data, re.MULTILINE)
    for key, value in matches:
        package_info.setdefault(key, []).append(value)

    return package_info

def run_script(script_path):
    """Run a shell script if it exists."""
    if os.path.exists(script_path):
        print(f"Running script: {script_path}")
        subprocess.run(["sudo", script_path], check=True, capture_output=True)

def install_package(package_path):
    """Install a package by moving files from cache to their respective directories."""
    package_info = parse_package(package_path)
    package_name = package_info.get('Package', ['Unnamed'])[0]
    if input(f"Are you sure you want to install {package_name}? (y/n): ").lower() == 'n':
        return

    control_path = os.path.join(CONF_PATH, os.path.basename(package_path))
    preinst_path = os.path.join(control_path, "preinst")
    postinst_path = os.path.join(control_path, "postinst")
    
    run_script(preinst_path)

    src_cache = os.path.join(CACHE_PATH, os.path.basename(package_path))
    src_dirs, src_paths = get_paths([], [], src_cache, src_cache)

    new_dirs = []
    new_files = []

    try:
        for src_dir in src_dirs:
            dest_path = os.path.join('/', src_dir)
            if not os.path.isdir(dest_path):
                mkdir(dest_path)
                new_dirs.append(dest_path)

        for src_path in src_paths:
            dest_path = os.path.join('/', src_path)
            src_path = os.path.join(src_cache, src_path)
            move(src_path, dest_path)
            new_files.append(dest_path)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred during file operations: {e}")
        for file_path in new_files:
            try:
                remove(file_path.strip())
            except OSError as e:
                print(f"Failed to remove file or directory {file_path.strip()}: {e}")
        sys.exit(1)

    run_script(postinst_path)

    print("Updating icon cache...")
    subprocess.run([
        "sudo", "find", "/usr/share/icons", "-name", "icon-theme.cache",
        "-exec", "rm", "-f", "{}", "+"
    ], check=True, capture_output=True)

    new_files.extend(new_dirs)
    with open(os.path.join(control_path, "new_files"), 'w', encoding='utf-8') as f:
        f.writelines(f"{file}\n" for file in new_files)

    with open(os.path.join(CONF_PATH, "installed_packages"), 'a+', encoding='utf-8') as f:
        f.write(f"{package_name}\n")

    os.rename(control_path, os.path.join(CONF_PATH, package_name))

    print(f"{package_name} has been installed")

def add_file(file_path, output):
    """Add an executable file to the system."""
    cache_path = os.path.join(CACHE_PATH, output)
    dest_path = os.path.join('/usr/local/bin', output)
    print(f"Adding executable file to {dest_path}")
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(f"#!/bin/bash\n{file_path} $*\n")
        os.chmod(cache_path, 0o755)
    except IOError as e:
        print(f"Failed to add file: {e}")
        sys.exit(1)
    move(cache_path, dest_path)
    with open(os.path.join(CONF_PATH, "added_files"), 'a+', encoding='utf-8') as f:
        f.write(f"{output}\n")
    print(f"{file_path} has been added")

def list_installed_packages():
    """List all installed packages."""
    print("Listing installed packages...")
    try:
        with open(os.path.join(CONF_PATH, "installed_packages"), 'r', encoding='utf-8') as f:
            print(f.read())
    except FileNotFoundError:
        print("No installed packages found.")

def uninstall(package):
    """Uninstall the specified package."""
    print(f"Uninstalling package: {package}")
    installed_packages_path = os.path.join(CONF_PATH, "installed_packages")
    control_path = os.path.join(CONF_PATH, package)
    prerm_path = os.path.join(control_path, "prerm")
    postrm_path = os.path.join(control_path, "postrm")

    try:
        with open(installed_packages_path, 'r+', encoding='utf-8') as f:
            installed_packages = f.readlines()
            if f"{package}\n" in installed_packages:
                if input(f"Are you sure you want to uninstall {package}? (y/n): ").lower() == 'n':
                    return
    
                run_script(prerm_path)

                with open(os.path.join(control_path, "new_files"), "r", encoding='utf-8') as file:
                    for file_path in file.readlines():
                        try:
                            remove(file_path.strip())
                        except OSError as e:
                            print(f"Failed to remove file or directory {file_path.strip()}: {e}")

                run_script(postrm_path)

                installed_packages.remove(f"{package}\n")
                f.seek(0)
                f.writelines(installed_packages)
                f.truncate()
                remove(control_path, privilege=1)
                print(f"{package} has already uninstalled.")
            else:
                print(f"Package {package} not found.")
    except FileNotFoundError:
        print("No installed packages found.")
    except Exception as e:
        print(f"Failed to uninstall package {package}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Dins: a simple package installer.")
    subparsers = parser.add_subparsers(dest='command')

    install_parser = subparsers.add_parser('install', help='Install software from the specified package path')
    install_parser.add_argument('package_path', type=str, help='Path to the package')

    add_parser = subparsers.add_parser('add', help='Add an executable file to the system')
    add_parser.add_argument('file_path', type=str, help='Path to the executable file')
    add_parser.add_argument('-o', '--output', type=str, required=True, help='Name of the executable in /usr/local/bin')

    uninstall_parser = subparsers.add_parser('uninstall', help='Uninstall software')
    uninstall_parser.add_argument('package', type=str, help='Package name to be uninstalled')

    subparsers.add_parser('list', help='List installed packages')

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if args.command == "install":
        package_path = os.path.abspath(args.package_path)
        cache_path = os.path.join(CACHE_PATH, os.path.basename(package_path))
        control_path = os.path.join(CONF_PATH, os.path.basename(package_path))
        os.makedirs(control_path, exist_ok=True)
        try:
            print(f"Extracting package: {package_path}")
            subprocess.run(["dpkg", "-x", package_path, cache_path], check=True, capture_output=True)
            print(f"Extracting control data: {package_path}")
            subprocess.run(["dpkg", "-e", package_path, control_path], check=True, capture_output=True)
            install_package(package_path)
        except subprocess.CalledProcessError as e:
            print(f"Error during installation: {e}")
            sys.exit(1)
    elif args.command == "add":
        add_file(os.path.abspath(args.file_path), args.output)
    elif args.command == "list":
        list_installed_packages()
    elif args.command == "uninstall":
        uninstall(args.package)

if __name__ == "__main__":
    check_usr()
    check_dir()
    try:
        main()
    finally:
        clean_cache()
