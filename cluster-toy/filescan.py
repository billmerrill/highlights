import os
import magic
from collections import namedtuple
from pathlib import Path

# Define the named tuple for file information
FileInfo = namedtuple('FileInfo', ['file_path', 'mime_type', 'file_size'])

def get_files_with_info(directory):
    """
    Generate a list of all non-zero length files in a directory and subdirectories.
    
    Args:
        directory (str): Path to the directory to scan
        
    Returns:
        list[FileInfo]: List of FileInfo named tuples containing:
            - file_path: Full path to the file
            - mime_type: MIME type of the file
            - file_size: Size of the file in bytes
            
    Raises:
        ValueError: If directory doesn't exist or isn't a directory
        ImportError: If python-magic library is not installed
    """
    # Validate input directory
    if not os.path.exists(directory):
        raise ValueError(f"Directory '{directory}' does not exist")
    
    if not os.path.isdir(directory):
        raise ValueError(f"'{directory}' is not a directory")
    
    # Try to initialize magic for MIME type detection
    try:
        mime_detector = magic.Magic(mime=True)
    except ImportError:
        raise ImportError("python-magic library is required. Install with: pip install python-magic")
    except Exception as e:
        raise RuntimeError(f"Failed to initialize magic library: {e}")
    
    file_list = []
    
    # Walk through directory and subdirectories
    for root, dirs, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            
            try:
                # Get file size
                file_size = os.path.getsize(file_path)
                
                # Skip zero-length files
                if file_size == 0:
                    continue
                
                # Get MIME type
                try:
                    mime_type = mime_detector.from_file(file_path)
                except Exception:
                    # Fallback for files that can't be analyzed
                    mime_type = 'application/octet-stream'
                
                # Create FileInfo tuple and add to list
                file_info = FileInfo(
                    file_path=file_path,
                    mime_type=mime_type,
                    file_size=file_size
                )
                file_list.append(file_info)
                
            except (OSError, IOError) as e:
                # Skip files that can't be accessed (permissions, etc.)
                print(f"Warning: Could not access {file_path}: {e}")
                continue
    
    return file_list

def get_files_with_info_fallback(directory):
    """
    Alternative version that works without python-magic library.
    Uses basic file extension mapping for MIME types.
    
    Args:
        directory (str): Path to the directory to scan
        
    Returns:
        list[FileInfo]: List of FileInfo named tuples
    """
    import mimetypes
    
    # Validate input directory
    if not os.path.exists(directory):
        raise ValueError(f"Directory '{directory}' does not exist")
    
    if not os.path.isdir(directory):
        raise ValueError(f"'{directory}' is not a directory")
    
    file_list = []
    
    # Walk through directory and subdirectories
    for root, dirs, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            
            try:
                # Get file size
                file_size = os.path.getsize(file_path)
                
                # Skip zero-length files
                if file_size == 0:
                    continue
                
                # Get MIME type using mimetypes module (based on extension)
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type is None:
                    mime_type = 'application/octet-stream'
                
                # Create FileInfo tuple and add to list
                file_info = FileInfo(
                    file_path=file_path,
                    mime_type=mime_type,
                    file_size=file_size
                )
                file_list.append(file_info)
                
            except (OSError, IOError) as e:
                # Skip files that can't be accessed
                print(f"Warning: Could not access {file_path}: {e}")
                continue
    
    return file_list

def format_file_size(size_bytes):
    """
    Helper function to format file size in human-readable format.
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def print_file_summary(file_list):
    """
    Print a summary of the files found.
    """
    if not file_list:
        print("No non-zero files found.")
        return
    
    print(f"\nFound {len(file_list)} non-zero files:")
    print("=" * 80)
    
    # Group by MIME type
    mime_counts = {}
    total_size = 0
    
    for file_info in file_list:
        mime_type = file_info.mime_type
        mime_counts[mime_type] = mime_counts.get(mime_type, 0) + 1
        total_size += file_info.file_size
    
    print(f"Total size: {format_file_size(total_size)}")
    print(f"\nFile types found:")
    for mime_type, count in sorted(mime_counts.items()):
        print(f"  {mime_type}: {count} files")
    
    print(f"\nFirst 10 files:")
    for i, file_info in enumerate(file_list[:10]):
        rel_path = os.path.relpath(file_info.file_path)
        size_str = format_file_size(file_info.file_size)
        print(f"  {i+1:2d}. {rel_path}")
        print(f"      Type: {file_info.mime_type}")
        print(f"      Size: {size_str}")
        print()

def main():
    """
    Example usage of the file analyzer function.
    """
    directory = input("Enter directory path to analyze: ").strip()
    
    try:
        # Try the full version first
        try:
            files = get_files_with_info(directory)
            print("Using python-magic for accurate MIME type detection.")
        except ImportError:
            print("python-magic not available, using fallback method.")
            print("For better MIME type detection, install with: pip install python-magic")
            files = get_files_with_info_fallback(directory)
        
        print_file_summary(files)
        
        # Example of accessing individual file info
        if files:
            print(f"\nExample - First file details:")
            first_file = files[0]
            print(f"Path: {first_file.file_path}")
            print(f"MIME Type: {first_file.mime_type}")
            print(f"Size: {first_file.file_size} bytes ({format_file_size(first_file.file_size)})")
            
            # Demonstrate named tuple access
            print(f"\nAccessing via named tuple attributes:")
            print(f"first_file.file_path = {first_file.file_path}")
            print(f"first_file.mime_type = {first_file.mime_type}")
            print(f"first_file.file_size = {first_file.file_size}")
        
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
