import subprocess
import sys
from pathlib import Path
import shutil
import json

def get_user_input(prompt, default=None):
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    return input(f"{prompt}: ").strip()

def yes_no_prompt(prompt, default=True):
    default_str = "Y/n" if default else "y/N"
    response = input(f"{prompt} [{default_str}]: ").strip()

    if not response:
        return default
    return response in ['y', 'yes']

def main():
    print("=" * 60)
    print("   DRAGONSREALM BUILD TOOL")
    print("   Version 1.0")
    print("=" * 60)
    print()

    #Get the path(s) to the user's web folders
    print("CONFIGURATION")
    print("-" * 60)

    current_folder = get_user_input(
        "Enter the CURRENT folder name (this includes files that you want to deploy as a new update)",
        "Current"
    )

    new_folder = get_user_input(
        "Enter the versioned folder name (where versioned files will go)",
        "Verioned"
    )

    use_previous = yes_no_prompt(
        "Do you have a PREVIOUS deployment to compare against? (e.g., files that have already been hosted live)",
        False
    )

    previous_folder = None
    if use_previous:
        previous_folder = get_user_input(
            "Enter the PREVIOUS folder name (for version comparison)",
            "Previous"
        )

    #Ensure folders exist
    current_path = Path(current_folder)
    if not current_path.exists():
        print(f"Folder '{current_folder}' does not exist!")
        sys.exit(1)

    if previous_folder:
        previous_path = Path(previous_folder)
        if not previous_path.exists():
            print(f"[Warning]  Folder '{previous_folder}' does not exist!")
            print(f"Continuing without version comparison...")
            previous_folder = None

    # Create new folder if it doesn't exist
    new_path = Path(new_folder)
    if new_path.exists():
        if yes_no_prompt(f"[Warning]  '{new_folder}' already exists. Replace it?", False):
            shutil.rmtree(new_path)
            print(f"Deleted old '{new_folder}' folder")
        else:
            print("Using existing folder (files may be overwritten)")

    #Run the versioning script
    print("VERSIONING FILES")
    print("-" * 60)

    try:
        #Change the version_manager.py's Configurations

        with open("version_config.json", "w", encoding='utf-8') as config_file:
            config_data = {
                "source_dir": f"{current_folder}/public",
                "output_dir": f"{new_folder}/public",
                "previous_version_dir": f"{previous_folder}/public" if previous_folder else None
            }
            json.dump(config_data, config_file, indent=4)

        # Run version_manager.py
        result = subprocess.run([sys.executable, "version_manager.py"],
                               capture_output=False, text=True)

        if result.returncode != 0:
            print("Versioning failed!")
            sys.exit(1)

        print("Versioning complete!")

    except Exception as e:
        print(f"Error during versioning: {e}")
        sys.exit(1)

    #After running the versioning, now run the minification script
    print("MINIFYING FILES")
    print("-" * 60)

    if yes_no_prompt("Remove all console.log lines from JavaScript?", True) is True:
        remove_console_logs = True
    else:
        remove_console_logs = False

    try:
        with open("minify_config.json", "w", encoding='utf-8') as config_file:
            config_data = {
                "source_dir": f"{new_folder}/public",
                "output_dir": "dist/public",
                "remove_console_logs": remove_console_logs,
                "verbose": "False"
            }

            json.dump(config_data, config_file, indent=4)

        # Run minification
        result = subprocess.run([sys.executable, "minification.py"],
                               capture_output=False, text=True)

        if result.returncode != 0:
            print("Minification failed!")
            sys.exit(1)

        print("Minification complete!")

    except Exception as e:
        print(f"Error during minification: {e}")
        sys.exit(1)

    print()

    # Step 5: Summary
    print("=" * 60)
    print("BUILD COMPLETE!")
    print("=" * 60)
    print(f"The processed files are in: dist2/")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Build Cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
