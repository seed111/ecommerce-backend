import os
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
_dynamodb = None


def get_dynamodb():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return _dynamodb


def get_table(table_name):
    return get_dynamodb().Table(table_name)


def put_item(table_name, item):
    try:
        get_table(table_name).put_item(Item=item)
        return item
    except ClientError as e:
        logger.error(f"DynamoDB put_item failed: {e.response['Error']}")
        raise


def get_item(table_name, key):
    try:
        response = get_table(table_name).get_item(Key=key)
        return response.get("Item")
    except ClientError as e:
        logger.error(f"DynamoDB get_item failed: {e.response['Error']}")
        raise


def query_by_index(table_name, index_name, key_name, key_value):
    try:
        response = get_table(table_name).query(
            IndexName=index_name,
            KeyConditionExpression=Key(key_name).eq(key_value),
        )
        return response.get("Items", [])
    except ClientError as e:
        logger.error(f"DynamoDB query failed: {e.response['Error']}")
        raise


def scan_table(table_name):
    try:
        return get_table(table_name).scan().get("Items", [])
    except ClientError as e:
        logger.error(f"DynamoDB scan failed: {e.response['Error']}")
        raise


def update_item(table_name, key, update_expression, expression_values, expression_names=None):
    kwargs = {
        "Key": key,
        "UpdateExpression": update_expression,
        "ExpressionAttributeValues": expression_values,
        "ReturnValues": "ALL_NEW",
    }
    if expression_names:
        kwargs["ExpressionAttributeNames"] = expression_names
    try:
        return get_table(table_name).update_item(**kwargs).get("Attributes", {})
    except ClientError as e:
        logger.error(f"DynamoDB update_item failed: {e.response['Error']}")
        raise