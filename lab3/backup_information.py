import boto3

dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')