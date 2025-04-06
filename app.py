import os
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import cv2
import base64
import boto3
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Flatten
from tensorflow.keras.optimizers import Adam
from dotenv import load_dotenv
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

app = Flask(__name__)
CORS(app, origins=["https://umangdoshi0.github.io"])

load_dotenv()

AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AES_KEY = os.getenv('AES_KEY', 'thisisasecretkey')[:16].encode()

s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
S3_BUCKET = "umangaws10"

# AES Encrypt
def aes_encrypt(data, key):
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ct = encryptor.update(data) + encryptor.finalize()
    return iv + ct

# AES Decrypt
def aes_decrypt(encrypted_data, key):
    aes_key = request.json.get("aes_key", "").strip().encode()
    if len(aes_key) not in [16, 24, 32]:
        return jsonify({"error": "Invalid AES key length."}), 401
    iv = encrypted_data[:16]
    ct = encrypted_data[16:]
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    return decryptor.update(ct) + decryptor.finalize()

# Encode image to base64
def encode_image(image):
    _, buffer = cv2.imencode(".png", image)
    return base64.b64encode(buffer).decode("utf-8")

# Decode image from base64
def decode_image(data):
    return cv2.imdecode(np.frombuffer(base64.b64decode(data), np.uint8), cv2.IMREAD_COLOR)

def clear_s3_shares():
    response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix="share_")
    if 'Contents' in response:
        for obj in response['Contents']:
            s3.delete_object(Bucket=S3_BUCKET, Key=obj['Key'])

@app.route("/encrypt", methods=["POST"])
def encrypt():
    file = request.files["image"]
    image = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)
    height, width, _ = image.shape
    n = random.randint(2, 5)

    def generate_random_share():
        choice = random.choice(["xor", "chaos", "deep_learning", "color_variation"])
        if choice == "xor":
            return np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
        elif choice == "chaos":
            return np.mod(np.random.random((height, width, 3)) * 500, 256).astype(np.uint8)
        elif choice == "deep_learning":
            try:
                model = Sequential([
                    Flatten(input_shape=(height, width, 3)),
                    Dense(512, activation='relu'),
                    Dense(height * width * 3, activation='sigmoid')
                ])
                model.compile(optimizer=Adam(), loss="binary_crossentropy")
                random_input = np.random.random((1, height, width, 3))
                adaptive_noise = model.predict(random_input).reshape((height, width, 3)) * 255
                return np.clip(np.uint8(adaptive_noise), 0, 255)
            except Exception as e:
                print(f"Deep learning share error: {e}")
                return np.zeros((height, width, 3), dtype=np.uint8)
        elif choice == "color_variation":
            share = np.zeros((height, width, 3), dtype=np.uint8)
            share[:, :, 0] = np.random.randint(0, 256, (height, width), dtype=np.uint8)
            share[:, :, 1] = np.random.randint(100, 200, (height, width), dtype=np.uint8)
            share[:, :, 2] = np.random.randint(50, 150, (height, width), dtype=np.uint8)
            return share

    shares = [generate_random_share() for _ in range(n - 1)]
    final_share = image.copy()
    for share in shares:
        final_share = cv2.bitwise_xor(final_share, share)
    shares.append(final_share)

    encoded_shares = [encode_image(share) for share in shares]
    return jsonify({"num_shares": n, "shares": encoded_shares})

@app.route("/upload", methods=["POST"])
def upload():
    shares = request.json["shares"]
    clear_s3_shares()
    for idx, share_b64 in enumerate(shares):
        encrypted_data = aes_encrypt(base64.b64decode(share_b64), AES_KEY)
        s3.put_object(Bucket=S3_BUCKET, Key=f"share_{idx}.enc", Body=encrypted_data)
    return jsonify({"message": "Uploaded successfully"})

@app.route("/fetch", methods=["POST"])
def fetch():
    num_shares = int(request.json["num_shares"])  # Get number of shares from the request
    key = request.json["aes_key"].encode()  # Get the AES key from the request and encode it
    
    if key != AES_KEY:
        return jsonify({"error": "Incorrect key. Please try again."}), 401  # Return 401 if keys don't match


    encrypted_shares = []
    
    # Step 1: Fetch the encrypted shares from S3
    for idx in range(num_shares):
        try:
            # Fetch the encrypted share from S3
            obj = s3.get_object(Bucket=S3_BUCKET, Key=f"share_{idx}.enc")
            encrypted_data = obj["Body"].read()
            encrypted_shares.append(encrypted_data)
        except Exception as e:
            # If fetching share fails, return a server error (500)
            print(f"Failed to fetch share_{idx}: {e}")
            return jsonify({"error": f"Failed to fetch share_{idx}. Please try again."}), 500

    # Step 2: Now attempt to decrypt each of the fetched shares using the provided AES key
    decrypted_shares = []
    for idx, encrypted_data in enumerate(encrypted_shares):
        try:
            # Try to decrypt the encrypted share using the AES key
            decrypted = aes_decrypt(encrypted_data, key)
            decrypted_b64 = base64.b64encode(decrypted).decode()  # Convert decrypted binary data to base64
            decrypted_shares.append(decrypted_b64)
        except Exception as e:
            # If decryption fails for any share, return a 401 Unauthorized response
            print(f"Decryption failed for share_{idx}: {e}")
            return jsonify({"error": "Incorrect key. Decryption failed for one or more shares."}), 401

    # Step 3: If all shares are successfully decrypted, return the decrypted shares
    return jsonify({"shares": decrypted_shares})


@app.route("/decrypt", methods=["POST"])
def decrypt():
    shares = request.json["shares"]
    decoded_shares = [decode_image(share) for share in shares]

    decrypted_image = decoded_shares[0]
    for share in decoded_shares[1:]:
        decrypted_image = cv2.bitwise_xor(decrypted_image, share)

    return jsonify({"decrypted_image": encode_image(decrypted_image)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)