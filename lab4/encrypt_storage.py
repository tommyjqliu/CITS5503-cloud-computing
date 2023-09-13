import boto3
import os, struct
from Crypto.Cipher import AES
from Crypto import Random
import boto3
import hashlib
import argparse
import sys
from tqdm import tqdm
from botocore.exceptions import ClientError
import logging
import time

ROOT_DIR = "./"
BUCKET_CONFIG = {"LocationConstraint": "ap-southeast-2"}
KMS_KEY_ID = "alias/22962256"
LOCAL_PASSWORD = "22962256-KEY"
BLOCK_SIZE = 16
CHUNK_SIZE = 64 * 1024

s3 = boto3.client("s3")
kms = boto3.client("kms")


def aws_encrypt_file(plainchunk):
    response = kms.encrypt(KeyId=KMS_KEY_ID, Plaintext=plainchunk)
    return response["CiphertextBlob"]


def aws_decrypt_file(cipherchunk):
    response = kms.decrypt(CiphertextBlob=cipherchunk)
    return response["Plaintext"]


def local_encrypt_file(plainchunk, encryptor):
    return encryptor.encrypt(plainchunk)


def local_decrypt_file(cipherchunk, decryptor):
    return decryptor.decrypt(cipherchunk)


def encrypt_file(in_filename, out_filename, mode):
    with open(in_filename, "rb") as infile:
        with open(out_filename, "wb") as outfile:
            filesize = os.path.getsize(in_filename)
            iv = Random.new().read(AES.block_size)
            outfile.write(struct.pack("<Q", filesize))
            outfile.write(iv)

            if mode == "local":
                local_key = hashlib.sha256(LOCAL_PASSWORD.encode("utf-8")).digest()
                encryptor = AES.new(local_key, AES.MODE_CBC, iv)

            while True:
                chunk = infile.read(CHUNK_SIZE)
                if len(chunk) == 0:
                    break
                elif len(chunk) % 16 != 0:
                    chunk += " ".encode("utf-8") * (16 - len(chunk) % 16)
                cipherchunk = (
                    local_encrypt_file(chunk, encryptor)
                    if mode == "local"
                    else aws_encrypt_file(chunk)
                )
                outfile.write(cipherchunk)


def decrypt_file(in_filename, out_filename, mode):
    with open(in_filename, "rb") as infile:
        origsize = struct.unpack("<Q", infile.read(struct.calcsize("Q")))[0]
        iv = infile.read(16)

        if mode == "local":
            local_key = hashlib.sha256(LOCAL_PASSWORD.encode("utf-8")).digest()
            decryptor = AES.new(local_key, AES.MODE_CBC, iv)

        with open(out_filename, "wb") as outfile:
            while True:
                chunk = infile.read(CHUNK_SIZE)
                if len(chunk) == 0:
                    break
                plainchunk = (
                    local_decrypt_file(chunk, decryptor)
                    if mode == "local"
                    else aws_decrypt_file(chunk)
                )
                outfile.write(plainchunk)

            outfile.truncate(origsize)


# Try to initialise bucket
def bucket_initialize(bucket_dir):
    s3 = boto3.client("s3")
    try:
        response = s3.create_bucket(
            Bucket=bucket_dir, CreateBucketConfiguration=BUCKET_CONFIG
        )
        print("Bucket created.\n", response)

    except Exception as error:
        type = sys.exc_info()
        # Only ignore duplicate bucket error
        if "BucketAlreadyOwnedByYou" not in str(type):
            raise error


def upload_file(filepath, bucket_dir):
    filename = os.path.basename(filepath)
    try:
        with tqdm(
            total=os.path.getsize(filepath),
            unit="B",
            unit_scale=True,
            desc=filename,
        ) as progress:
            s3.upload_file(
                filepath,
                bucket_dir,
                filepath[2:],
                Callback=lambda bytes_transferred: progress.update(bytes_transferred),
            )

    except ClientError as e:
        logging.error(e)
        return False
    return True


def download_file(file, bucket_dir):
    key = file["Key"]
    filepath = ROOT_DIR + key
    filename = os.path.basename(filepath)
    directory = os.path.dirname(filepath)

    if not os.path.exists(directory):
        os.makedirs(directory)

    try:
        with tqdm(
            total=file["Size"],
            unit="B",
            unit_scale=True,
            desc=filename,
        ) as progress:
            with open(filepath, "wb") as f:
                s3.download_fileobj(
                    bucket_dir,
                    key,
                    f,
                    Callback=lambda bytes_transferred: progress.update(
                        bytes_transferred
                    ),
                )

    except ClientError as e:
        logging.error(e)
        return False
    return True


class FileControler:
    def __init__(self, mode="local"):
        self.mode = mode
        self.bucket_dir = "22962256-cloudstorage-encryptmode-" + mode
        bucket_initialize(self.bucket_dir)

    def backup_files(self):
        for dir_name, subdir_list, file_list in os.walk(ROOT_DIR, topdown=True):
            if dir_name != ROOT_DIR:
                for fname in file_list:
                    origin_path = "%s/%s" % (dir_name, fname)
                    encrtpted_path = "%s/%s.encrtpted" % (dir_name, fname)
                    encrypt_file(origin_path, encrtpted_path, self.mode)
                    upload_file(encrtpted_path, self.bucket_dir)
                    os.remove(encrtpted_path)

    def restore_file(self):
        files = s3.list_objects(Bucket=self.bucket_dir)["Contents"]
        for file in files:
            key = file["Key"]
            encrtpted_path = ROOT_DIR + key
            origin_path = encrtpted_path.replace(".encrtpted", "")
            download_file(file, self.bucket_dir)
            decrypt_file(encrtpted_path, origin_path, self.mode)
            os.remove(encrtpted_path)


file_controler = FileControler(mode="aws")
aws_start_time = time.time()
file_controler.backup_files()
aws_uploaded_time = time.time()
file_controler.restore_file()
aws_downloaded_time = time.time()

file_controler = FileControler(mode="local")
local_start_time = time.time()
file_controler.backup_files()
local_uploaded_time = time.time()
file_controler.restore_file()
local_downloaded_time = time.time()

print(f"Aws encrypt upload time: {aws_uploaded_time-aws_start_time} seconds")
print(f"Aws encrypt download time: {aws_downloaded_time-aws_uploaded_time} seconds")
print(f"Local encrypt upload time: {local_uploaded_time-local_start_time} seconds")
print(f"Local encrypt download time: {local_downloaded_time-local_uploaded_time} seconds")
