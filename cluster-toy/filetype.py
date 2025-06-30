import magic
import mimetypes
import imghdr
import sndhdr
import struct
import os

def detect_with_python_magic(file_path):
    """
    Uses python-magic library (libmagic wrapper).
    Most accurate method - install with: pip install python-magic
    
    On Windows, you may also need: pip install python-magic-bin
    """
    try:
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(file_path)
        
        # Get human-readable description too
        description = magic.from_file(file_path)
        
        return {
            'mime_type': file_type,
            'description': description,
            'method': 'python-magic'
        }
    except Exception as e:
        return {'error': str(e), 'method': 'python-magic'}

def detect_with_filetype(file_path):
    """
    Uses filetype library - pure Python, no dependencies.
    Install with: pip install filetype
    """
    try:
        import filetype
        kind = filetype.guess(file_path)
        if kind is None:
            return {'mime_type': 'unknown', 'method': 'filetype'}
        
        return {
            'mime_type': kind.mime,
            'extension': kind.extension,
            'method': 'filetype'
        }
    except ImportError:
        return {'error': 'filetype library not installed', 'method': 'filetype'}
    except Exception as e:
        return {'error': str(e), 'method': 'filetype'}

def detect_image_type(file_path):
    """
    Uses built-in imghdr module for images.
    No external dependencies needed.
    """
    try:
        image_type = imghdr.what(file_path)
        if image_type:
            return {
                'type': image_type,
                'mime_type': f'image/{image_type}',
                'method': 'imghdr'
            }
        return {'type': None, 'method': 'imghdr'}
    except Exception as e:
        return {'error': str(e), 'method': 'imghdr'}

def detect_audio_type(file_path):
    """
    Uses built-in sndhdr module for audio files.
    No external dependencies needed.
    """
    try:
        audio_type = sndhdr.what(file_path)
        if audio_type:
            return {
                'type': audio_type[0],
                'mime_type': f'audio/{audio_type[0]}',
                'method': 'sndhdr'
            }
        return {'type': None, 'method': 'sndhdr'}
    except Exception as e:
        return {'error': str(e), 'method': 'sndhdr'}

def detect_by_magic_bytes(file_path):
    """
    Manual detection using magic bytes/file signatures.
    Fast and reliable for common formats.
    """
    magic_bytes = {
        b'\x89PNG\r\n\x1a\n': 'image/png',
        b'\xff\xd8\xff': 'image/jpeg',
        b'GIF8': 'image/gif',
        b'RIFF': 'audio/wav',  # or video/avi - need more bytes to distinguish
        b'\x1f\x8b': 'application/gzip',
        b'PK\x03\x04': 'application/zip',
        b'PK\x05\x06': 'application/zip',
        b'PK\x07\x08': 'application/zip',
        b'%PDF': 'application/pdf',
        b'\x7fELF': 'application/x-executable',
        b'MZ': 'application/x-executable',  # Windows PE
        b'\xca\xfe\xba\xbe': 'application/java-vm',  # Java class
        b'\xfe\xed\xfa': 'application/x-executable',  # Mach-O
    }
    
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)  # Read first 16 bytes
            
        for magic, mime_type in magic_bytes.items():
            if header.startswith(magic):
                return {
                    'mime_type': mime_type,
                    'magic_bytes': magic.hex(),
                    'method': 'magic_bytes'
                }
        
        # Special cases that need more analysis
        if header.startswith(b'RIFF') and len(header) >= 12:
            if header[8:12] == b'WAVE':
                return {'mime_type': 'audio/wav', 'method': 'magic_bytes'}
            elif header[8:12] == b'AVI ':
                return {'mime_type': 'video/avi', 'method': 'magic_bytes'}
        
        return {'mime_type': 'unknown', 'method': 'magic_bytes'}
        
    except Exception as e:
        return {'error': str(e), 'method': 'magic_bytes'}

def detect_text_encoding(file_path):
    """
    Detect if file is text and what encoding it uses.
    """
    try:
        import chardet
        
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # Read first 10KB
            
        result = chardet.detect(raw_data)
        
        if result['confidence'] > 0.7:  # High confidence it's text
            return {
                'encoding': result['encoding'],
                'confidence': result['confidence'],
                'mime_type': 'text/plain',
                'method': 'chardet'
            }
        
        return {'mime_type': 'binary', 'method': 'chardet'}
        
    except ImportError:
        # Fallback without chardet
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1000)
            return {'mime_type': 'text/plain', 'encoding': 'utf-8', 'method': 'utf8_test'}
        except UnicodeDecodeError:
            return {'mime_type': 'binary', 'method': 'utf8_test'}
    except Exception as e:
        return {'error': str(e), 'method': 'chardet'}

def comprehensive_file_detection(file_path):
    """
    Combines multiple methods for best results.
    """
    if not os.path.exists(file_path):
        return {'error': 'File does not exist'}
    
    results = {}
    
    # Try different methods
    methods = [
        detect_with_python_magic,
        detect_with_filetype,
        detect_image_type,
        detect_audio_type,
        detect_by_magic_bytes,
        detect_text_encoding
    ]
    
    for method in methods:
        try:
            result = method(file_path)
            method_name = result.get('method', method.__name__)
            results[method_name] = result
        except Exception as e:
            results[method.__name__] = {'error': str(e)}
    
    # Determine best result
    best_result = None
    
    # Prefer python-magic if available
    if 'python-magic' in results and 'error' not in results['python-magic']:
        best_result = results['python-magic']
    elif 'filetype' in results and 'error' not in results['filetype']:
        best_result = results['filetype']
    elif 'magic_bytes' in results and results['magic_bytes'].get('mime_type') != 'unknown':
        best_result = results['magic_bytes']
    
    return {
        'best_guess': best_result,
        'all_results': results,
        'file_size': os.path.getsize(file_path)
    }

def main():
    """
    Example usage and testing
    """
    test_file = input("Enter file path to analyze: ").strip()
    
    if not os.path.exists(test_file):
        print("File does not exist!")
        return
    
    print(f"\nAnalyzing: {test_file}")
    print("=" * 50)
    
    # Comprehensive analysis
    result = comprehensive_file_detection(test_file)
    
    if result['best_guess']:
        print("BEST GUESS:")
        for key, value in result['best_guess'].items():
            print(f"  {key}: {value}")
    
    print(f"\nFile size: {result['file_size']} bytes")
    
    print("\nALL METHODS:")
    for method, data in result['all_results'].items():
        print(f"\n{method}:")
        for key, value in data.items():
            print(f"  {key}: {value}")

if __name__ == "__main__":
    main()
