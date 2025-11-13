# Compactify

Python based tool for processing website files for maximum efficiency on hosted speed and bandwidth. Also applies versioning to file names in order to allow hosting to have maximum cache for `.css` `.js`, automatically adds a version number to files and smartly incredments by 0.0.1. 

I intentionally built this for a website project I was/am working on called `DragonsRealm` (You can see this on my main GitHub profile). My intention was to try and optimise web files that are hosted via a free tier plan on Firebase. With some changes to headers, Firebase supports features like choosing how long certain file types (css, html, etc.) are cached for or not cached at all, and also serves files such as .br compressed web files.

Most website projects should be able to use these python files even though they intended for a specific project in mind, it "should" apply to most website projects.

---

## What it does
- **Automatic File Versioning (cache busting)** - Adds a version numbers to all files. Version numbers can be found as `.001.` before the file's format. This doesn't version:
    - Any files in `assets/dist` (A specific use case for a web project I intentionally made this for)
    - any wasm files
    - HTML files
    - Anything outside of `public` folder (A specific use case for a web project and it's folder structure)

- **version Increment** - It reads a given folder containing files that are actively deployed live to a new folder for an updated version, reads and compares all files and only change the version number in file name when there's been any change.

- **File referencing update** - All JavaScript, HTML and CSS files that reference another file (such as importing a file) will also update to match teh correct version in the referenced file's name

- **JavaScript Minification** - uses Terser to aggressively minify JavaScript.

- **HTML & CSS** - Minifies HTMl and CSS, removing all the unrequired parts in each file.

- **Brotli Compression** - Creates `br` files for maximum compression but also keeps uncompressed to deploy as an alternitive for when a client web browser doesn't support Brotli.

## Prerequisites

### Required Software:
1. **Python 3.13** (Have not tested on any other versions)
2. **Node.js V22** (Again, haven't tried any other versions)

### Required Python Packages:
- brotli

### Required Node Packages:
- terser

## Folder Structure

To make this build script work, it's important to have the correct files and folders in the right place.
Your workspace should look like this:

```
C:\Users\YourName\Desktop\folder\
│
├── build.py     # Main build script
├── version_manager.py    # Handles file versioning
├── minification.py     # Handles minification & compression
├── minify.js       # JavaScript minifier (Terser config)
│
├── Current/           # Your web files to run through the python scripts
│
├── Previous/       # Last deployed version of the webfiles (optional if Previous isn't available)
│
├── New/         # Auto-generated versioned files (Created by version_manager.py)
│
└── dist2/            # Folder containing the completed files ready to deploy (Created by minification.py)
```

Since I made this specifically for Firebase project. The folder structure I had for web files was:

```
Current/
│
├── public/
  │
  ├── website files and folders
│
├── Important firebase files that are needed for firebase but not hosting specific.
```

Here "public/" can contain any web files in any structure, the python scripts don't depend on a specific structure inside the public folder as it iterates through all files in all folders inside the "public" folder.
The files inside "Current/" aren't versioned, only inside the public folder are files versioned, but any files found inside "Current/" are copied over to the final output folder (created with minification.py)

---

## How It Works

### Step 1: Versioning (`version_manager.py`)
```
Current/public/  >    New/public/
  styles.css          styles.001.css
  script.js           script.001.js
  image.jpg           image.001.jpg
  index.html          index.html (updated references)
```

**What happens:**
- Adds `.001` to new files
- Compares with `Previous/` folder (if provided)
- Increments version if file content changed
- Updates all references in HTML/JS/CSS
- Copies non-public files as-is

### Step 2: Minification (`minification.py`)
```
New/public/          >           dist2/public/
  styles.001.css (10 KB)      styles.001.css (7 KB)
  script.001.js (50 KB)       script.001.js (25 KB)
  index.html (5 KB)           index.html (3 KB)
```
> File sizes above are example numbers and not in anyway representing the actual potential size compressions.

**What happens:**
- Minifies HTML (removes whitespace, comments)
- Minifies CSS (optimizes colors, removes unused code)
- Minifies JavaScript (using Terser via `minify.js`)
- Creates `.br` Brotli-compressed files
- Copies images and other assets over to the newly created output folder.



![GitHub issues](https://img.shields.io/github/issues/jamster3000/Compactify)
![Last Commit](https://img.shields.io/github/last-commit/jamster3000/Compactify)
![GitHub Stars](https://img.shields.io/github/stars/jamster3000/Compactify?style=social)![Code Size](https://img.shields.io/github/languages/code-size/jamster3000/Compactify)
