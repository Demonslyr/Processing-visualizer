"""
Build script for Spectrum Visualizer executable.

Usage:
    python build.py          # Build the executable
    python build.py --clean  # Clean build artifacts and rebuild
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def clean_build_dirs():
    """Remove build artifacts."""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    files_to_clean = ['*.pyc']
    
    root = Path(__file__).parent
    
    for dir_name in dirs_to_clean:
        dir_path = root / dir_name
        if dir_path.exists():
            print(f"Removing {dir_path}")
            shutil.rmtree(dir_path)
    
    # Clean pycache in src
    for pycache in root.rglob('__pycache__'):
        print(f"Removing {pycache}")
        shutil.rmtree(pycache)


def build():
    """Build the executable using PyInstaller."""
    root = Path(__file__).parent
    spec_file = root / 'spectrum_visualizer.spec'
    
    if not spec_file.exists():
        print(f"Error: Spec file not found: {spec_file}")
        sys.exit(1)
    
    print("=" * 60)
    print("Building Spectrum Visualizer")
    print("=" * 60)
    
    # Run PyInstaller
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        str(spec_file)
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(root))
    
    if result.returncode != 0:
        print("\nBuild failed!")
        sys.exit(1)
    
    # Check output
    exe_path = root / 'dist' / 'SpectrumVisualizer.exe'
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 60)
        print(f"Build successful!")
        print(f"Executable: {exe_path}")
        print(f"Size: {size_mb:.1f} MB")
        print("=" * 60)
        
        # Copy config.yaml next to exe if it exists
        config_src = root / 'config.yaml'
        config_dst = root / 'dist' / 'config.yaml'
        if config_src.exists() and not config_dst.exists():
            shutil.copy(config_src, config_dst)
            print(f"Copied config.yaml to dist/")
    else:
        print("\nBuild completed but executable not found!")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Build Spectrum Visualizer executable')
    parser.add_argument('--clean', action='store_true', help='Clean build artifacts first')
    args = parser.parse_args()
    
    if args.clean:
        clean_build_dirs()
    
    build()


if __name__ == '__main__':
    main()
