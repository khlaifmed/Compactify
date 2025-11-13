import re
import shutil
from pathlib import Path
import subprocess
import json
import brotli

class WebMinifier:
    def __init__(self, source_dir, output_dir=None, create_backup=True, should_obfuscate_js=False, super_minify=False, remove_console_logs=True, enable_brotli=True, verbose=False):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir) if output_dir else None
        self.create_backup = create_backup
        self.should_obfuscate_js = should_obfuscate_js
        self.super_minify = super_minify
        self.remove_console_logs = remove_console_logs
        self.enable_brotli = enable_brotli
        self.verbose = verbose
        self.stats = {
            'html': 0, 'css': 0, 'js': 0, 'other': 0, 
            'bytes_saved': 0, 'console_logs_removed': 0, 'brotli_bytes_saved': 0
        }

    def minify_html(self, content):
        # Preserve content inside <script> and <style> tags
        scripts = []
        styles = []
        
        def save_script(match):
            scripts.append(match.group(0))
            return f'___SCRIPT_{len(scripts)-1}___'
        
        def save_style(match):
            styles.append(match.group(0))
            return f'___STYLE_{len(styles)-1}___'
  
        # Temporarily replace scripts and styles
        content = re.sub(r'<script[^>]*>.*?</script>', save_script, content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<style[^>]*>.*?</style>', save_style, content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML comments (but not conditional comments for IE)
        content = re.sub(r'<!--(?!\[if)(?!<!)[^\[].*?-->', '', content, flags=re.DOTALL)
        
        # Remove whitespace between tags
        content = re.sub(r'>\s+<', '><', content)
    
        # Remove leading/trailing whitespace on lines
        content = re.sub(r'^\s+', '', content, flags=re.MULTILINE)
        content = re.sub(r'\s+$', '', content, flags=re.MULTILINE)
        
        # Collapse multiple spaces to one
        content = re.sub(r' {2,}', ' ', content)
 
        # Remove spaces around equals signs in attributes
        content = re.sub(r'\s*=\s*', '=', content)
        
        # Remove quotes from attributes where safe
        if self.super_minify:
            content = re.sub(r'=(["\'])([a-zA-Z0-9\-_]+)\1', r'=\2', content)
            
            # Remove optional closing tags for void elements (but keep self-closing slashes for XHTML compatibility)
            content = re.sub(r'</(?:p|li|dt|dd|option|thead|tbody|tfoot|tr|th|td|colgroup)>(?=\s*<(?:/|li|dt|dd|option|tr|th|td|thead|tbody|tfoot|table))', '', content)
        
        # Restore scripts and styles
        for i, script in enumerate(scripts):
            content = content.replace(f'___SCRIPT_{i}___', script)
        for i, style in enumerate(styles):
            content = content.replace(f'___STYLE_{i}___', style)
        
        return content.strip()

    def minify_css(self, content):
        # Remove CSS comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        # Remove whitespace around CSS delimiters
        content = re.sub(r'\s*([{}:;,>~+\[\]])\s*', r'\1', content)
        
        # Remove semicolon before closing brace
        content = re.sub(r';}', '}', content)
      
        # Collapse multiple spaces to one
        content = re.sub(r'\s+', ' ', content)
 
        # Remove space after colons
        content = re.sub(r':\s+', ':', content)
        
        # Remove all newlines
        content = content.replace('\n', '').replace('\r', '')
 
        # Convert colors to shorter hex format
        content = self._optimize_css_colors(content)
        
        # Remove redundant units (e.g., 0px > 0)
        content = re.sub(r'\b0(?:px|em|rem|%|pt|cm|mm|in|pc|ex|ch|vw|vh|vmin|vmax)\b', '0', content)
   
        # Simplify floating point numbers (0.5 > .5)
        content = re.sub(r'\b0+\.(\d+)', r'.\1', content)
      
        # Remove leading zeros from numbers
        content = re.sub(r':0+\.(\d+)', r':.\1', content)
  
        # Simplify margin/padding shorthands
        content = re.sub(r':(\d+(?:px|em|rem|%)?)\s+\1\s+\1\s+\1(?=[;}])', r':\1', content)
        content = re.sub(r':(\d+(?:px|em|rem|%)?)\s+(\d+(?:px|em|rem|%)?)\s+\1\s+\2(?=[;}])', r':\1 \2', content)
        
        # Remove quotes from URLs where possible
        content = re.sub(r'url\(["\']([^"\']+)["\']\)', r'url(\1)', content)
        
        # Shorten font weights
        content = content.replace('font-weight:normal', 'font-weight:400')
        content = content.replace('font-weight:bold', 'font-weight:700')
  
        # Remove unnecessary zeros in decimals (.00 > 0)
        content = re.sub(r'\.0+([^\d]|$)', r'0\1', content)
        
        # Remove empty rules
        content = re.sub(r'[^}]+\{\s*\}', '', content)
 
        return content.strip()

    def _optimize_css_colors(self, content):
        color_map = {
            'white': '#fff', 'black': '#000', 'red': '#f00', 'lime': '#0f0',
            'blue': '#00f', 'yellow': '#ff0', 'cyan': '#0ff', 'magenta': '#f0f',
            'silver': '#c0c0c0', 'gray': '#808080', 'grey': '#808080',
            'maroon': '#800000', 'olive': '#808000', 'green': '#008000',
            'purple': '#800080', 'teal': '#008080', 'navy': '#000080',
            'orange': '#ffa500', 'fuchsia': '#f0f'
        }
        
        for name, hex_val in color_map.items():
            # Only replace if the hex is shorter
            if len(hex_val) < len(name):
                content = re.sub(rf'\b{name}\b', hex_val, content, flags=re.IGNORECASE)
        
        # Optimize hex colors: #ffffff > #fff, #ff0000 > #f00
        def shorten_hex(match):
            hex_color = match.group(0).lower()
            if len(hex_color) == 7:
                if hex_color[1] == hex_color[2] and hex_color[3] == hex_color[4] and hex_color[5] == hex_color[6]:
                    return '#' + hex_color[1] + hex_color[3] + hex_color[5]
            return hex_color
        
        content = re.sub(r'#[0-9a-fA-F]{6}\b', shorten_hex, content)
        
        # Convert rgb(255,255,255) to #fff where appropriate
        def rgb_to_hex(match):
            r, g, b = map(int, match.groups())
            if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
                hex_color = f'#{r:02x}{g:02x}{b:02x}'
                # Try to shorten
                if hex_color[1] == hex_color[2] and hex_color[3] == hex_color[4] and hex_color[5] == hex_color[6]:
                    return '#' + hex_color[1] + hex_color[3] + hex_color[5]
            return hex_color
            return match.group(0)
     
        content = re.sub(r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', rgb_to_hex, content)
        
        return content

    def remove_console_statements(self, content):
        if not self.remove_console_logs:
            return content, 0
      
        original = content
        console_count = 0   

        #Pattern match for console statements including nested in parentheses and multi-line
        #Doesn't remove warning or error
        patterns = [
            # Standard console statements with semicolon
            (r'console\.(log|info|debug|trace|table|dir|dirxml|group|groupCollapsed|groupEnd|time|timeEnd|assert|count|profile|profileEnd)\s*\([^;]*?\);?', 're'),
            # Console statements without semicolon (end of line or before another statement)
            (r'^\s*console\.(log|info|debug|trace|table|dir|dirxml|group|groupCollapsed|groupEnd|time|timeEnd|assert|count|profile|profileEnd)\s*\([^\n;]*?\)\s*$', 're.MULTILINE'),
        ]
        
        for pattern, flags_str in patterns:
            flags = re.MULTILINE if 'MULTILINE' in flags_str else 0
            matches = re.findall(pattern, content, flags)
            console_count += len(matches)
            content = re.sub(pattern, '', content, flags=flags)
   
        # Clean up empty lines left behind
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        return content, console_count

    def minify_js(self, input_path):
        try:
            relative_path = input_path.relative_to(self.source_dir)
   
            output_file = self.output_dir / relative_path
            output_file = output_file.with_suffix('.js')
            output_file.parent.mkdir(parents=True, exist_ok=True)

            result = subprocess.run([
                'node', 'minify.js', str(input_path), str(output_file)
            ], capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                print(f"JavaScript minification failed for {input_path.name}: {result.stderr.strip()}")
            else:
                if self.verbose:
                   print(f"JavaScript minified: {relative_path}")
        except Exception as e:
            print(f"Unexpected error during JavaScript minification: {e}")

    def copy_file(self, file_path):
        if not self.output_dir:
            return
        
        relative_path = file_path.relative_to(self.source_dir)
        output_path = self.output_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, output_path)
        self.stats['other'] += 1
        
        if self.verbose:
            print(f"> {file_path.name}: Copied")

    def minify_file(self, file_path):
        file_path = Path(file_path)
        ext = file_path.suffix.lower()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except UnicodeDecodeError:
            print(f"Skipping {file_path.name}: Unable to decode as UTF-8")
            return
        except Exception as e:
            print(f"Skipping {file_path.name}: Error reading file - {e}")
            return
        
        original_size = len(original_content)
        minified_content = original_content
        
        if self.verbose:
            print(f"\nProcessing {file_path.name}...")
        
        # Minify based on file type
        try:
            if ext == '.html':
                minified_content = self.minify_html(original_content)
                self.stats['html'] += 1
            elif ext == '.css':
                minified_content = self.minify_css(original_content)
                self.stats['css'] += 1
            elif ext == '.js':
                if self.output_dir:
                    self.minify_js(file_path)
                else:
                    print(f"Output directory not specified for {file_path.name}")
                self.stats['js'] += 1
                return
            else:
                return
        except Exception as e:
            print(f"[Error]  minifying {file_path.name}: {e}")
            return
        
        minified_size = len(minified_content)
        bytes_saved = original_size - minified_size
        self.stats['bytes_saved'] += bytes_saved
    
        if self.output_dir:
            relative_path = file_path.relative_to(self.source_dir)
            output_path = self.output_dir / relative_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            output_path = file_path
            # Create backup if overwriting
            if self.create_backup and bytes_saved > 0:
                backup_path = file_path.with_suffix(file_path.suffix + '.bak')
                try:
                    shutil.copy2(file_path, backup_path)
                    if self.verbose:
                        print(f"  Created backup: {backup_path.name}")
                except Exception as e:
                    print(f"⚠️  Failed to create backup: {e}")
   
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(minified_content)
        except Exception as e:
            print(f"[Error]  writing {output_path.name}: {e}")
            return
        
        if bytes_saved > 0:
            reduction_pct = (bytes_saved / original_size * 100) if original_size > 0 else 0
            print(f"{file_path.name}: {original_size:,} → {minified_size:,} bytes ({reduction_pct:.1f}% reduction)")
        else:
            print(f"{file_path.name}: No reduction (already optimized or gained bytes)")

    def compress_with_brotli(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                data = f.read()

            original_size = len(data)

            #11 is the max compression level
            compressed = brotli.compress(data, quality=11)

            br_path = file_path.with_suffix(file_path.suffix + '.br')
            with open(br_path, 'wb') as f:
                f.write(compressed)

            compressed_size = len(compressed)
            savings = original_size - compressed_size
            self.stats['brotli_bytes_saved'] += savings

            if self.verbose:
                reduction_pct = (savings / original_size * 100) if original_size > 0 else 0
                print(f"> Brotli: {file_path.name} → {file_path.name}.br ({reduction_pct:.1f}% reduction, saved {savings:,} bytes)")

            return True
        except Exception as e:
            if self.verbose:
                print(f"Brotli compression failed for {file_path.name}: {e}")
            return False

    def minify_directory(self):
        if not self.source_dir.exists():
            print(f"[Error]  Directory '{self.source_dir}' does not exist")
            return
        
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        all_files = [f for f in self.source_dir.rglob('*') if f.is_file()]
    
        if not all_files:
            print("[Error]  No files found")
            return
        
        minifiable_extensions = {'.html', '.css', '.js'}
        minifiable_files = [f for f in all_files if f.suffix.lower() in minifiable_extensions]
        other_files = [f for f in all_files if f.suffix.lower() not in minifiable_extensions]
        
        print(f"{'='*60}")
        print(f"Found {len(minifiable_files)} files to minify:")
        print(f"  - HTML: {len([f for f in minifiable_files if f.suffix.lower() == '.html'])}")
        print(f"  - CSS:  {len([f for f in minifiable_files if f.suffix.lower() == '.css'])}")
        print(f"  - JS:   {len([f for f in minifiable_files if f.suffix.lower() == '.js'])}")
        print(f"Found {len(other_files)} other files to copy")
        print(f"{'='*60}\n")
   
        # Process minifiable files
        for file_path in minifiable_files:
            self.minify_file(file_path)
        
        # Copy other files that don't get minified
        if self.output_dir and other_files:
            print(f"\n{'='*60}")
            print("Copying non-minifiable files...")
            print(f"{'='*60}")
            for file_path in other_files:
                self.copy_file(file_path)
        
        # Brotli compression
        if self.enable_brotli and self.output_dir:
            print(f"\n{'='*60}")
            print("Compressing files with Brotli...")
            print(f"{'='*60}")

            compressible_extensions = {'.html', '.css', '.js', '.json', '.xml', '.svg', '.txt'}
            output_files = [f for f in self.output_dir.rglob('*') 
                            if f.is_file() and f.suffix.lower() in compressible_extensions]

            for file_path in output_files:
                self.compress_with_brotli(file_path)

        # Print summary
        print(f"\n{'='*60}")
        print("MINIFICATION SUMMARY")
        print(f"{'='*60}")
        print(f"HTML files processed:  {self.stats['html']}")
        print(f"CSS files processed:         {self.stats['css']}")
        print(f"JS files processed:          {self.stats['js']}")
        print(f"Other files copied:          {self.stats['other']}")
        print(f"Total bytes saved:           {self.stats['bytes_saved']:,} bytes ({self.stats['bytes_saved']/1024:.2f} KB)")
   
        if self.remove_console_logs and self.stats['console_logs_removed'] > 0:
            print(f"Console statements removed:  {self.stats['console_logs_removed']}")

        if self.enable_brotli and self.stats['brotli_bytes_saved'] > 0:
            print(f"Brotli compression saved: {self.stats['brotli_bytes_saved']:,} bytes ({self.stats['brotli_bytes_saved']/1024:.2f} KB)")
            total_saved = self.stats['bytes_saved'] + self.stats['brotli_bytes_saved']
            print(f"TOTAL BYTES SAVED: {total_saved:,} bytes ({total_saved/1024:.2f} KB)")

        print(f"{'='*60}")

if __name__ == "__main__":
    try:
        with open("minify_config.json", "r", encoding='utf-8') as config_file:
            config = json.load(config_file)
            source_dir = config.get("source_dir")
            output_dir = config.get("output_dir")
            remove_console_logs = config.get("remove_console_logs", True)
            verbose = config.get("verbose", True)

        minifier = WebMinifier(
            source_dir=source_dir,
            output_dir=output_dir,
            remove_console_logs=remove_console_logs,
            verbose=verbose
        )
        minifier.minify_directory()
    except FileNotFoundError:
        print("version_config.json not found. Please ensure the file exists before running again")
    except Exception as e:
        print(f"Error reading version_config.json: {e}")
