
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

def _convert_key_to_der_test(private_key_raw: str) -> bytes:
    private_key_raw = private_key_raw.strip()
    if "BEGIN" in private_key_raw and "END" in private_key_raw:
        print("Detected PEM format.")
        private_key = serialization.load_pem_private_key(
            private_key_raw.encode("utf-8"),
            password=None,
            backend=default_backend()
        )
        return private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    else:
        print("Assuming base64-encoded DER format.")
        try:
            der_bytes = base64.b64decode(private_key_raw)
            # Try to load it as a DER private key to confirm it's valid DER
            serialization.load_der_private_key(der_bytes, password=None, backend=default_backend())
            print("Successfully decoded base64 and loaded as DER private key.")
            return der_bytes
        except Exception as e:
            print(f"Error during base64 decode or DER loading: {e}")
            raise ValueError(
                "Private key format not recognized. "
                "Expected PEM format or base64-encoded DER." + str(e)
            )

private_key_b64der = "MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCRqkkwx4Mq9/Iwc6flLHbl+GL9YF4rTTFo5hMHTew4169xI8lQWBFpz3nwUlTZF7t+qs0QXzio/MAtHDlJrTu/d9JkN9dq4AYwSlSW1AbWNf3TTyaPlrvZReBoTHz4w5q4A8U90A2yPGenn27HsefFvTh1Igs6FAGgqS4xRc/aYgOOPwyu2yZ7ZA7h/DxDHweBqedLj/XoufKzkXXXUXYYlWCwubETiPHoSIY+ZyYUCfxfIj+I/gQzOgDR6RI+ddnSyar3jL6+YA+a9YW2pay8+UyFZ6QVnY5UtgdKoMWWtc7fcq5zjG8TomXRyEh5+Lyu7v1difIGOPAeYXHY97WLAgMBAAECggABRj9/biFtRu/PIXXotQHBy5FnJNiSEany4F9ufw2n5iguadkdKzYUykhHdFrybskYx7sFT4X2AYcXZfGw3bOB/nUAZDYt5NGdCstwaeC4704+EulUFIYmdZxr4S5vOTvhbAQF4Uv7YRipkGUmWV29HsWPjcmSG6JzgsNpEjKqNxGumMwZ3qTMO2E5ni4TvXaAB9KrIb8mL6EOk3PzwnbSlugnfJvVTC6p2F8hDCkLDIj669WKw+SJiKUxtV/2BwWUJ/uUVTFwQ8jXhiOIzhHrWRO+6BD9mQp9jxaUfmEva8zog8S72mhOJsoeaFLW2+g5ahmCm9De6IzgIJ91KCINQKBgQDColXw8rYrJLPZXyWlCg+o+Fu7RmtimcZlAy13Q1wVHej6nROEbJvAOwZXWfmFYFBwSiqQlsKGjCxxW/JHoFbJZYreW6L82dCB8yhHaTLiz4DNtOF3EzHXFmPwFnU2KJqKfVYSJrhQ3uYWiib0ef/0bcX+V9fjqHBw+SX3BEZvBQKBgQC/l3q9V3c6A0jskY8C3CysgXWYs8ENc1OpR3atbVDtGAniE/pqiAA+HDFlV9NUJiftGVkIQOXMmb6ZZ4jFMSHc8kTG/7Du80AzKVhZ9Bsfdwstgb+mby4eOVGGuzE6k4+0+oFnZNHQmpolHHWEzs4M7K/Pi/CvHD3n0j5mVdoXTwKBgGV25WCP1wHUx2FZZbGM9i77Ei8l/dNQIQoFxwz2c6mahxsnCcauK9/hpWOiRx8N38E6GMh5n30u0/hgm4RVhQjGw8c5dFVmY3lrPqNDp0BwNlCGrEc8HW5ogL7npkEOl8n8nwMlZk7adI5phPdMJm/RTjdSqfxHkh6C9BS3CNDVAoGATIywjMBKsdIoK+VIl6Ly8oXTP4zqoH4ouiUEhP+rGuAU6tCCqFfoiOho0A4UMLYCE9ih2wtbBbGUFuToH6mu1wGxezUkM4TbbNWjKGXBBIRi4e7KbSxU59yM92EJnVbh/zRryazdrBRpbFR/m+2pJD7ZS/qk0sJc9afqKKc6uT8CgYAVy17iVWnlikzWQhG5m/BK3HCbe0BcYmcmmxNfH2xgINtWNLzbw3UXVZPOSWcTAJd19rOh4+D6nppPyKm6/XcrrOdpbNewCZn1GspmWZdmNx90wC77sfWE/dMX7E5dnkjAAiij03yhB2EbW1opPYD/mlBJwPL4MSBZdPAoikL7vg=="

try:
    der_bytes_result = _convert_key_to_der_test(private_key_b64der)
    print(f"DER bytes (first 20): {der_bytes_result[:20]}")
    print(f"DER bytes length: {len(der_bytes_result)}")
except Exception as e:
    print(f"Test failed: {e}")
