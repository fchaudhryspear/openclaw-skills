
import base64

# Test with a simple known string
original_string = "Hello, Base64!"
encoded_string = base64.b64encode(original_string.encode("utf-8")).decode("utf-8")

print(f"Original string: {original_string}")
print(f"Encoded string: {encoded_string}")
print(f"Length of encoded string: {len(encoded_string)}")

try:
    decoded_bytes = base64.b64decode(encoded_string)
    decoded_string = decoded_bytes.decode("utf-8")
    print("Base64 decoding successful!")
    print(f"Decoded string: {decoded_string}")
    print(f"Length of decoded bytes: {len(decoded_bytes)}")
except Exception as e:
    print(f"Base64 decoding failed: {e}")
