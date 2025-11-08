import os

def flatten_directory(source_dir, output_file="flattened_output.txt", include_exts=None, 
                     exclude_exts=None, exclude_dirs=None, max_file_size=500_000, max_lines=300):
    """
    Flattens a directory by writing all file contents and paths into a single text file.

    Args:
        source_dir (str): Path to the directory to flatten.
        output_file (str): Output text file path.
        include_exts (list[str], optional): File extensions to include (e.g., ['.py', '.js']).
        exclude_exts (list[str], optional): File extensions to exclude.
        exclude_dirs (list[str], optional): Directory names to skip (e.g., ['node_modules', 'venv', '__pycache__']).
        max_file_size (int): Skip files larger than this (in bytes).
        max_lines (int): Maximum number of lines to include per file (default 300).
    """
    # Default directories to exclude
    if exclude_dirs is None:
        exclude_dirs = ['.git', '__pycache__', 'node_modules', 'venv', '.venv', 'env', 
                       'dist', 'build', '.idea', '.vscode', 'site-packages']
    
    # Default extensions to exclude
    if exclude_exts is None:
        exclude_exts = ['.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib', '.exe']
    
    with open(output_file, "w", encoding="utf-8") as out:
        out.write(f"Flattened view of: {os.path.abspath(source_dir)}\n")
        out.write("=" * 80 + "\n\n")

        for root, dirs, files in os.walk(source_dir):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            rel_path = os.path.relpath(root, source_dir)
            out.write(f"\n📁 Directory: {rel_path}\n")
            out.write("-" * 80 + "\n")

            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()

                # Extension filtering
                if include_exts and ext not in include_exts:
                    continue
                if exclude_exts and ext in exclude_exts:
                    continue

                # Skip large files
                if os.path.getsize(file_path) > max_file_size:
                    out.write(f"[Skipped: {file} — too large]\n")
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    
                    # Limit lines
                    truncated = len(lines) > max_lines
                    content_lines = lines[:max_lines]
                    
                    out.write(f"\n--- FILE: {file_path} ---\n")
                    out.write(''.join(content_lines))
                    
                    if truncated:
                        out.write(f"\n[... truncated {len(lines) - max_lines} lines ...]\n")
                    
                    out.write("\n--- END OF FILE ---\n\n")
                except Exception as e:
                    out.write(f"[Error reading {file_path}: {e}]\n")

    print(f"\n✅ Flattened directory written to: {output_file}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Flatten a code directory into one text file.")
    parser.add_argument("directory", help="Path to directory to flatten")
    parser.add_argument("-o", "--output", default="flattened_output.txt", help="Output text file name")
    parser.add_argument("--include", nargs="*", help="File extensions to include (e.g., .py .js .html)")
    parser.add_argument("--exclude", nargs="*", help="File extensions to exclude")
    parser.add_argument("--exclude-dirs", nargs="*", help="Directory names to skip")
    parser.add_argument("--max-lines", type=int, default=300, help="Max lines per file (default 300)")
    args = parser.parse_args()

    flatten_directory(
        source_dir=args.directory,
        output_file=args.output,
        include_exts=args.include,
        exclude_exts=args.exclude,
        exclude_dirs=args.exclude_dirs,
        max_lines=args.max_lines
    )