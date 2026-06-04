import json
import logging
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

PRODUCTS_TABLE = os.environ["PRODUCTS_TABLE_NAME"]
ORDERS_TABLE = os.environ["ORDERS_TABLE_NAME"]

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "eu-west-1"))
products_table = dynamodb.Table(PRODUCTS_TABLE)
orders_table = dynamodb.Table(ORDERS_TABLE)


def lambda_handler(event, context):
    logger.info(json.dumps({"message": "Processing stream event", "record_count": len(event["Records"])}))

    for record in event["Records"]:
        if record["eventName"] != "INSERT":
            continue

        new_image = record["dynamodb"]["NewImage"]
        order_id = new_image["order_id"]["S"]
        user_id = new_image["user_id"]["S"]
        items = _deserialize_list(new_image.get("items", {}).get("L", []))

        logger.info(json.dumps({"message": "Processing order", "order_id": order_id}))
        _decrement_stock(items, order_id)
        _confirm_order(order_id, user_id)

    return {"status": "ok"}


def _decrement_stock(items, order_id):
    for item in items:
        product_id = item.get("product_id")
        quantity = int(item.get("quantity", 1))
        try:
            products_table.update_item(
                Key={"product_id": product_id},
                UpdateExpression="SET stock = stock - :qty",
                ConditionExpression=Attr("stock").gte(quantity),
                ExpressionAttributeValues={":qty": Decimal(str(quantity))},
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ValueError(f"Insufficient stock for {product_id}")
            raise


def _confirm_order(order_id, user_id):
    from datetime import datetime, timezone
    orders_table.update_item(
        Key={"order_id": order_id, "user_id": user_id},
        UpdateExpression="SET #s = :status, processed_at = :ts",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": "CONFIRMED",
            ":ts": datetime.now(timezone.utc).isoformat(),
        },
    )


def _deserialize_list(dynamo_list):
    return [{k: list(v.values())[0] for k, v in item["M"].items()} for item in dynamo_list if "M" in item]