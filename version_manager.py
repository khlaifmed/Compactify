import os
import re
import hashlib
import shutil
from pathlib import Path
import json

class VersionManager:
    def __init__(self, source_dir, output_dir, previous_version_dir=None):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.previous_version_dir = Path(previous_version_dir) if previous_version_dir else None
        self.version_map = {}  # Maps original filename to versioned filename

    def get_file_hash(self, file_path):
        #Get a file's hash for comparison for any changes that have been made
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def extract_version_number(self, filename):
        # Match version pattern: .001. followed by extension, OR .001 at the end
        match = re.search(r'\.(\d{3})(?:\.|$)', filename)
        if match:
            return int(match.group(1))
        return None

    def add_version_to_filename(self, filename, version=1):
        # Check if filename already ends with just a version number
        if re.search(r'\.\d{3}$', filename):
            # Already has version at the end, don't add another
            return filename
        
        name, ext = os.path.splitext(filename)
        return f"{name}.{version:03d}{ext}"

    def increment_version(self, filename):
        #Get the version number of the given file
        current_version = self.extract_version_number(filename)

        if current_version is None:
            return self.add_version_to_filename(filename, 1)

        # Check if the file has a version number at the end
        if re.search(r'\.\d{3}$', filename):
            #Replace the version at the end with new version number
            name_without_version = re.sub(r'\.\d{3}$', '', filename)
            return f"{name_without_version}.{current_version + 1:03d}"
        else:
            name_without_version = re.sub(r'\.\d{3}\.', '.', filename)
            name, ext = os.path.splitext(name_without_version)
            return f"{name}.{current_version + 1:03d}{ext}"

    def should_increment_version(self, current_file, relative_path):
        if not self.previous_version_dir:
            return False

        previous_file = self.previous_version_dir / relative_path
        if not previous_file.exists():
            return True

        current_hash = self.get_file_hash(current_file)
        previous_hash = self.get_file_hash(previous_file)
        return current_hash != previous_hash

    def get_versioned_filename(self, file_path):
        filename = file_path.name
        relative_path = file_path.relative_to(self.source_dir)

        #Ignore HTMl files, they shouldn't be versioned and always have no-cache headers
        if file_path.suffix.lower() == '.html':
            self.version_map[filename] = filename
            return filename

        #Ignore any .wasm files - they can be part of libraries that aren't looking with the version number
        if file_path.suffix.lower() == '.wasm':
            self.version_map[filename] = filename
            return filename

        # Don't version files inside assets/dist directory
        # This is a specific requirement for my own website files
        if 'assets' in relative_path.parts and 'dist' in relative_path.parts:
            self.version_map[filename] = filename
            return filename

        current_version = self.extract_version_number(filename)

        if current_version is None:
            # If no version is found, add .001 to filename
            versioned_name = self.add_version_to_filename(filename, 1)
        else:
            #File has a version - check if the file content has changed compared to last time
            if self.should_increment_version(file_path, relative_path):
                versioned_name = self.increment_version(filename)
            else:
                versioned_name = filename

        self.version_map[filename] = versioned_name
        return versioned_name

    def update_references_in_content(self, content):
        for original_name, versioned_name in self.version_map.items():
            if original_name != versioned_name:
                # Replace references to the original filename with versioned filename
                # This doesn't touch URLs so libary CDNs are safe
  
                parts = re.split(r'(https?://[^\s"\'<>)\]]+)', content)
   
                updated_parts = []
                for i, part in enumerate(parts):
                    if i % 2 == 0:  # Even indices are non-URL parts
                        part = re.sub(r'\b' + re.escape(original_name) + r'\b', versioned_name, part)
                        escaped_for_regex = original_name.replace('.', r'\.')
                        part = re.sub(re.escape(escaped_for_regex), versioned_name.replace('.', r'.'), part)
     
                    # Odd indices are URLs
                    updated_parts.append(part)
       
                content = ''.join(updated_parts)
 
        return content

    def process_files(self):
        # Create output directory
        self.output_dir.parent.mkdir(parents=True, exist_ok=True)

        #Copy all files from source root (outside public/) to output root
        source_root = self.source_dir.parent
        output_root = self.output_dir.parent
      
        for item in source_root.iterdir():
            if item.name == 'public':
                continue

            dest = output_root / item.name
            if item.is_file():
                shutil.copy2(item, dest)
                print(f"  Copied: {item.name}")
            elif item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
                print(f"  Copied directory: {item.name}")

        print("\n" + "=" * 60)
        print("VERSIONING FILES IN PUBLIC/")
        print("=" * 60)

        # Create output directory for public files
        self.output_dir.mkdir(parents=True, exist_ok=True)

        #Version all files in public/ 
        all_files = list(self.source_dir.rglob('*'))

        for file_path in all_files:
            if not file_path.is_file():
                continue

            relative_path = file_path.relative_to(self.source_dir)

            versioned_name = self.get_versioned_filename(file_path)

            # Copy file with new name
            output_path = self.output_dir / relative_path.parent / versioned_name
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, output_path)

            if versioned_name != file_path.name:
                print(f"  {file_path.name} -> {versioned_name}")

        #Update references in HTML, JavaScript, and CSS files
        for file_path in self.output_dir.rglob('*'):
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() not in ['.html', '.js', '.css']:
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Update references
                updated_content = self.update_references_in_content(content)

                if updated_content != content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)
                    print(f"Updated references in: {file_path.name}")

            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")

        print("\n" + "=" * 60)
        print("VERSIONING COMPLETE")
        print("=" * 60)

if __name__ == "__main__":
    try:
        with open("version_config.json", "r", encoding='utf-8') as config_file:
            config_data = json.load(config_file)
            source_dir = config_data.get("source_dir")
            output_dir = config_data.get("output_dir")
            previous_version_dir = config_data.get("previous_version_dir")

        manager = VersionManager(source_dir, output_dir, previous_version_dir)
        manager.process_files()
    except FileNotFoundError:
        print("version_config.json not found. Please ensure the file exists before running again")
    except Exception as e:
        print(f"Error reading version_config.json: {e}")
