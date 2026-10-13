import os

def ensure_dir(directory):
    """Create directory if it doesn't exist."""
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_file_extension(file_path):
    """Extract file extension."""
    return os.path.splitext(file_path)[1].lower()

def categorize_file(file_path, file_types):
    """Categorize file based on extension."""
    ext = get_file_extension(file_path)
    for file_type, extensions in file_types.items():
        if ext in extensions:
            return file_type
    return "unknown"