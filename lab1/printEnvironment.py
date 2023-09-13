import boto3
from tabulate import tabulate

ec2 = boto3.client("ec2")
response = ec2.describe_regions()


def getData(region):
    return [region["Endpoint"], region["RegionName"]]


print(tabulate(map(getData, response["Regions"]), headers=["Endpoint", "RegionName"]))
