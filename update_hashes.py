import hashlib
import os

# The files we are protecting
CRITICAL_FILES = [
    'core/services/tracker.py',
    'core/models.py',
    'core/views.py'
]

def calculate_hashes():
    print("re-calculating hashes for integrity protection...\n")
    print("replace the 'CRITICAL_HASHES' dictionary in 'core/integrity.py' with this:\n")
    
    print("CRITICAL_HASHES = {")
    
    for rel_path in CRITICAL_FILES:
        try:
            with open(rel_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
                print(f"    '{rel_path}': '{file_hash}',")
        except FileNotFoundError:
            print(f"    # ERROR: Could not find {rel_path}")
            
    print("}")
    print("\n[Done] Copy the block above and update core/integrity.py")

if __name__ == "__main__":
    calculate_hashes()
