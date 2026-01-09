import hashlib
import os
import sys

# Pre-calculated SHA256 hashes of critical files
# If you (the owner) change these files, you MUST update these hashes.
# Run: python3 -c "import hashlib; print(hashlib.sha256(open('filename', 'rb').read()).hexdigest())"
CRITICAL_HASHES = {
    'core/services/tracker.py': '5bb4a0f7f23e3aca3ba75a6b4fc2c645c42f834f950137690b3f6fb22ad55cf2',
    'core/models.py': '3be99053a3987cfd13ed5fdd38d040186e1a2906961947b0d6472ce35fc28679',
    'core/views.py': 'd86adcbd8a08b11bec4c4b8005f94142178725b1cd016f8eeb16a35392a1bd15'
}

def verify_integrity(base_dir):
    """
    Verifies that critical files have not been modified.
    Exits the program if a mismatch is found.
    """
    # print("Verifying system integrity...")
    
    for rel_path, expected_hash in CRITICAL_HASHES.items():
        full_path = os.path.join(base_dir, rel_path)
        
        if not os.path.exists(full_path):
            print(f"[CRITICAL] Missing component: {rel_path}")
            sys.exit(1)
            
        try:
            with open(full_path, 'rb') as f:
                content = f.read()
                current_hash = hashlib.sha256(content).hexdigest()
                
            if current_hash != expected_hash:
                print(f"\n[SECURITY ALERT] File integrity violation detected!")
                print(f"Modified file: {rel_path}")
                print("The application has detected unauthorized changes to the core codebase.")
                print("Anti-tamper protection engaged. Halting execution.")
                sys.exit(1)
                
        except Exception as e:
            print(f"[ERROR] Integrity check failed: {e}")
            sys.exit(1)
            
    # print("System integrity verified.")
