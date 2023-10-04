import boto3
import os

# Constant setting
ROOT_DIR = "./"
ROOT_S3_DIR = "22962256-cloudstorage"
BUCKET_CONFIG = {"LocationConstraint": "ap-southeast-2"}

s3_client = boto3.client("s3")
dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')

# use path as the primary key
table = dynamodb.create_table(
    TableName="CloudFiles",
    KeySchema=[
        {"AttributeName": "path", "KeyType": "HASH"},
        {"AttributeName": "userId", "KeyType": "RANGE"},
    ],
    AttributeDefinitions=[
        {"AttributeName": "path", "AttributeType": "S"},
        {"AttributeName": "userId", "AttributeType": "S"},
    ],
    ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
)

files = s3_client.list_objects(Bucket=ROOT_S3_DIR)["Contents"]
for file in files:
		# Get permission information of filr
    acl = s3_client.get_object_acl(Bucket=ROOT_S3_DIR, Key=file["Key"])
    permissions = acl["Grants"]
    table.put_item(
        Item={
            "userId": file["Owner"]["ID"],
            "fileName": os.path.basename(file["Key"]),
            "path": file["Key"],
            "lastUpdated": str(file["LastModified"]),
            "owner": file["Owner"]["DisplayName"],
            "permissions": str(permissions),
        }
    )