
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

def get_public_key_for_snowflake(private_key_pem: str) -> str:
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
        backend=default_backend()
    )
    public_key_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    
    # Snowflake expects the public key without headers/footers and no newlines
    public_key_snowflake = "".join(public_key_pem.splitlines()[1:-1])
    return public_key_snowflake

private_pem_content = """
-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCRqkkwx4Mq9/Iw
c6flLHbl+GL9YF4rTTFo5hMHTew4169xI8lQWBFpz3nwUlTZF7t+qs0QXzio/MAt
HDlJrTu/d9JkN9dq4AYwSlSW1AbWNf3TTyaPlrvZReBoTHz4w5q4A8U90A2yPGen
n27HsefFvTh1Igs6FAGgqS4xRc/aYgOOPwyu2yZ7ZA7h/DxDHweBqedLj/XoufKz
kXXXUXYYlWCwubETiPHoSIY+ZyYUCfxfIj+I/gQzOgDR6RI+ddnSyar3jL6+YA+a
9YW2pay8+UyFZ6QVnY5UtgdKoMWWtc7fcq5zjG8TomXRyEh5+Lyu7v1difIGOPAe
YXHY97WLAgMBAAECggEABRj9/biFtRu/PIXXotQHBy5FnJNiSEany4F9ufw2n5ig
uadkdKzYUykhHdFrybskYx7sFT4X2AYcXZfGw3bOB/nUAZDYt5NGdCstwaeC4704
+EulUFIYmdZxr4S5vOTvhbAQF4Uv7YRipkGUmWV29HsWPjcmSG6JzgsNpEjKqNxG
umMwZ3qTMO2E5ni4TvXaAB9KrIb8mL6EOk3PzwnbSlugnfJvVTC6p2F8hDCkLDIj
669WKw+SJiKUxtV/2BwWUJ/uUVTFwQ8jXhiOIzhHrWRO+6BD9mQp9jxaUfmEva8z
og8S72mhOJsoeaFLW2+g5ahmCm9De6IzgIJ91KCINQKBgQDColXw8rYrJLPZXyWl
Cg+o+Fu7RmtimcZlAy13Q1wVHej6nROEbJvAOwZXWfmFYFBwSiqQlsKGjCxxW/JH
oFbJZYreW6L82dCB8yhHaTLiz4DNtOF3EzHXFmPwFnU2KJqKfVYSJrhQ3uYWiib0
ef/0bcX+V9fjqHBw+SX3BEZvBQKBgQC/l3q9V3c6A0jskY8C3CysgXWYs8ENc1Op
R3atnVDtGAniE/pqiAA+HDFlV9NUJiftGVkIQOXMmb6ZZ4jFMSHc8kTG/7Du80Az
KVhZ9Bsfdwstgb+mby4eOVGGuzE6k4+0+oFnZNHQmpolHHWEzs4M7K/Pi/CvHD3n
0j5mVdoXTwKBgGV25WCP1wHUx2FZZbGM9i77Ei8l/dNQIQoFxwz2c6mahxsnCcau
K9/hpWOiRx8N38E6GMh5n30u0/hgm4RVhQjGw8c5dFVmY3lrPqNDp0BwNlCGrEc8
HW5ogL7npkEOl8n8nwMlZk7adI5phPdMJm/RTjdSqfxHkh6C9BS7CNDVAoGATIyw
jMBKsdIoK+VIl6Ly8oXTP4zqoH4ouiUEhP+rGuAU6tCCqFfoiOho0A4UMLYCE9ih
2wtbBbGUFuToH6mu1wGxezUkM4TbbNWjKGXBBIRi4e7KbSxU59yM92EJnVbh/zRr
yazdrBRpbFR/m+2pJD7ZS/qk0sJc9afqKKc6uT8CgYAVy17iVWnlikzWQhG5m/BK
3HCbe0BcYmcmmxNfH2xgINtWNLzbw3UXVZPOSWcTAJd19rOh4+D6nppPyKm6/Xcr
rOdpbNewCZn1GspmWZdmNx90wC77sfWE/dMX7E5dnkjAAiij03yhB2EbW1opPYD/
mlBJwPL4MSBZdPAoikL7vg==
-----END PRIVATE KEY-----
"""

try:
    public_key_for_snowflake = get_public_key_for_snowflake(private_pem_content)
    print(f"Public Key for Snowflake ALTER USER:\n{public_key_for_snowflake}")
except Exception as e:
    print(f"Error generating public key: {e}")
