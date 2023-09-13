import os
import boto3
from tqdm import tqdm
from botocore.exceptions import ClientError
import logging

# Constant setting
ROOT_DIR = "./"
ROOT_S3_DIR = "22962256-cloudstorage"
BUCKET_CONFIG = {"LocationConstraint": "ap-southeast-2"}

# Client initialise
s3_client = boto3.client("s3")


def download_file(file):
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
                s3_client.download_fileobj(
                    ROOT_S3_DIR,
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


response = s3_client.list_objects(Bucket=ROOT_S3_DIR)

for file in response["Contents"]:
    download_file(file)
