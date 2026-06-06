import os
import pytest
import boto3
from moto import mock_aws
from fastapi.testclient import TestClient

os.environ.update({
    "ENV": "test",
    "AWS_DEFAULT_REGION": "eu-west-1",
    "AWS_ACCESS_KEY_ID": "testing",
    "AWS_SECRET_ACCESS_KEY": "testing",
    "PRODUCTS_TABLE_NAME": "test-products",
    "ORDERS_TABLE_NAME": "test-orders",
    "USERS_TABLE_NAME": "test-users",
    "S3_BUCKET_NAME": "test-bucket",
})


@pytest.fixture(scope="function")
def aws_resources():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
        dynamodb.create_table(
            TableName="test-products",
            BillingMode="PAY_PER_REQUEST",
            KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "product_id", "AttributeType": "S"},
                {"AttributeName": "category", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[{
                "IndexName": "category-index",
                "KeySchema": [{"AttributeName": "category", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }],
        )
        dynamodb.create_table(
            TableName="test-orders",
            BillingMode="PAY_PER_REQUEST",
            KeySchema=[
                {"AttributeName": "order_id", "KeyType": "HASH"},
                {"AttributeName": "user_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "order_id", "AttributeType": "S"},
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "status", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "user-orders-index",
                    "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "status-index",
                    "KeySchema": [{"AttributeName": "status", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
        )
        dynamodb.create_table(
            TableName="test-users",
            BillingMode="PAY_PER_REQUEST",
            KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "email", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[{
                "IndexName": "email-index",
                "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }],
        )
        s3 = boto3.client("s3", region_name="eu-west-1")
        s3.create_bucket(
            Bucket="test-bucket",
            CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
        )
        yield


@pytest.fixture
def client(aws_resources):
    from main import app
    return TestClient(app)


def test_create_and_get_product(client):
    payload = {
        "name": "Test Sneaker",
        "description": "A great sneaker",
        "price": 99.99,
        "category": "footwear",
        "stock": 50,
    }
    response = client.post("/products/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Sneaker"
    product_id = data["product_id"]
    response = client.get(f"/products/{product_id}")
    assert response.status_code == 200
    assert response.json()["product_id"] == product_id


def test_create_user_and_prevent_duplicate(client):
    payload = {"name": "Fayemi", "email": "fayemi@example.com"}
    r1 = client.post("/users/", json=payload)
    assert r1.status_code == 201
    r2 = client.post("/users/", json=payload)
    assert r2.status_code == 409


def test_create_order(client):
    product = client.post("/products/", json={
        "name": "Jacket", "description": "Warm", "price": 150.0,
        "category": "clothing", "stock": 10,
    }).json()
    user = client.post("/users/", json={
        "name": "Test User", "email": "user@test.com",
    }).json()
    response = client.post("/orders/", json={
        "user_id": user["user_id"],
        "items": [{"product_id": product["product_id"], "quantity": 2}],
    })
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "PENDING"
    assert data["total_amount"] == 300.0


def test_product_not_found(client):
    response = client.get("/products/nonexistent-id")
    assert response.status_code == 404
