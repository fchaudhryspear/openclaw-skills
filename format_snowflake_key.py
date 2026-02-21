#!/usr/bin/env python3
"""
Snowflake Private Key Formatter for Lambda

This script properly formats RSA private keys for Snowflake JWT authentication.
Snowflake requires the private key in DER format (PKCS#8), not PEM.

Usage:
    python3 format_snowflake_key.py <path_to_private_key.pem>
    
Or provide the key directly and it will output the properly formatted version.
"""

import sys
import base64
from pathlib import Path

try:
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("Installing cryptography library...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography", "-q"])
    from cryptography.hazmat.primitives import serialization


def format_key_for_snowflake(private_key_pem: str) -> bytes:
    """
    Convert PEM private key to DER format for Snowflake.
    
    Snowflake's Python connector expects the private key as raw DER bytes (PKCS#8),
    not as a PEM string.
    
    Args:
        private_key_pem: The private key in PEM format (with headers)
        
    Returns:
        The private key in DER format (PKCS#8) as bytes
    """
    # Load the private key from PEM
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
    )
    
    # Convert to DER format (PKCS#8)
    private_key_der = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    
    return private_key_der


def format_key_for_environment(private_key_pem: str) -> str:
    """
    Convert PEM private key to base64-encoded DER for environment variable storage.
    
    This is useful when you need to store the key in an environment variable
    or Secrets Manager as a string.
    
    Args:
        private_key_pem: The private key in PEM format
        
    Returns:
        Base64-encoded DER key (safe for JSON/env vars)
    """
    der_bytes = format_key_for_snowflake(private_key_pem)
    return base64.b64encode(der_bytes).decode("utf-8")


def generate_new_key_pair():
    """Generate a new RSA key pair for Snowflake."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    private_key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    
    public_key_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    
    # Snowflake expects the public key without headers/footers
    public_key_snowflake = "".join(public_key_pem.splitlines()[1:-1])
    
    return private_key_pem, public_key_snowflake


def main():
    print("=" * 60)
    print("Snowflake Private Key Formatter")
    print("=" * 60)
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--generate":
        # Generate new key pair
        print("Generating new RSA key pair...")
        private_pem, public_key = generate_new_key_pair()
        
        print("\n--- PRIVATE KEY (PEM format - save this securely) ---")
        print(private_pem)
        
        print("\n--- PUBLIC KEY (for Snowflake ALTER USER) ---")
        print(public_key)
        
        print("\n--- PRIVATE KEY (Base64 DER for Lambda env var) ---")
        b64_der = format_key_for_environment(private_pem)
        print(b64_der[:80] + "...")  # Truncate for display
        
        print("\n⚠️  IMPORTANT: Store the private key securely!")
        print("   Use AWS Secrets Manager or Parameter Store.")
        return
    
    # Check if a file was provided
    if len(sys.argv) > 1:
        key_path = Path(sys.argv[1])
        if key_path.exists():
            private_key_pem = key_path.read_text()
        else:
            print(f"Error: File not found: {key_path}")
            sys.exit(1)
    else:
        print("Paste your private key (PEM format, including BEGIN/END lines):")
        print("(Press Ctrl+D when done)")
        private_key_pem = sys.stdin.read()
    
    if not private_key_pem.strip():
        print("Error: No key provided")
        sys.exit(1)
    
    try:
        # Convert to DER
        der_bytes = format_key_for_snowflake(private_key_pem)
        b64_der = base64.b64encode(der_bytes).decode("utf-8")
        
        print("\n" + "=" * 60)
        print("FORMATTED KEY (Base64-encoded DER)")
        print("=" * 60)
        print()
        print("Store this in your Lambda environment variable or Secrets Manager:")
        print()
        print(b64_der)
        print()
        print("=" * 60)
        print()
        print("Lambda code to use this key:")
        print("-" * 60)
        print('''
import base64
import os
import snowflake.connector
from cryptography.hazmat.primitives import serialization

# If stored as base64 in env var:
private_key_der = base64.b64decode(os.environ["SNOWFLAKE_PRIVATE_KEY"])

# Or if stored as PEM in Secrets Manager:
# private_key = serialization.load_pem_private_key(
#     private_key_pem.encode("utf-8"), password=None
# )
# private_key_der = private_key.private_bytes(
#     encoding=serialization.Encoding.DER,
#     format=serialization.PrivateFormat.PKCS8,
#     encryption_algorithm=serialization.NoEncryption(),
# )

conn = snowflake.connector.connect(
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    user=os.environ["SNOWFLAKE_USER"],
    private_key=private_key_der,  # DER format bytes
    warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
    database=os.environ["SNOWFLAKE_DATABASE"],
)
''')
        print("-" * 60)
        
    except Exception as e:
        print(f"Error formatting key: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
