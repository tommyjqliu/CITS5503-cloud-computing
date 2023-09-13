import os
import sys
import boto3
import argparse
from tqdm import tqdm
from botocore.exceptions import ClientError
import logging


# ------------------------------
# CITS5503
#
# cloudstorage.py
# Given a root local directory, will return files in each level and
# copy to same path on S3
#
# ------------------------------

# Constant setting
ROOT_DIR = "./"
ROOT_S3_DIR = "22962256-cloudstorage"
BUCKET_CONFIG = {"LocationConstraint": "ap-southeast-2"}

# Client initialise
s3_client = boto3.client("s3")



def upload_file(filepath):
    filename = os.path.basename(filepath)
    try:
        with tqdm(
            total=os.path.getsize(filepath),
            unit="B",
            unit_scale=True,
            desc=filename,
        ) as progress:
            s3_client.upload_file(
                filepath,
                ROOT_S3_DIR,
                filepath[2:],
                # store the original path
                ExtraArgs={"Metadata": {"OriginPath": filepath}},
                Callback=lambda bytes_transferred: progress.update(bytes_transferred),
            )

    except ClientError as e:
        logging.error(e)
        return False
    return True


def main():
    # Parse argument
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--initialise", help="Try to create a bucket on S3.", default=True
    )
    args = parser.parse_args()

    # Try to initialise bucket
    if args.initialise:
        try:
            response = s3_client.create_bucket(
                Bucket=ROOT_S3_DIR, CreateBucketConfiguration=BUCKET_CONFIG
            )
            print("Bucket created.\n", response)

        except Exception as error:
            type = sys.exc_info()
            # Only ignore duplicate bucket error
            if "BucketAlreadyOwnedByYou" not in str(type):
                raise error

    # Traverse and upload
    for dir_name, subdir_list, file_list in os.walk(ROOT_DIR, topdown=True):
        if dir_name != ROOT_DIR:
            for fname in file_list:
                upload_file("%s/%s" % (dir_name, fname))


if __name__ == "__main__":
    main()
