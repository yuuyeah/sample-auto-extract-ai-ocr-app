import boto3
import json
import os
from datetime import datetime, timezone


def handler(event, context):
    print(f"Event: {json.dumps(event)}")

    if event['RequestType'] == 'Delete':
        return {'PhysicalResourceId': 'demo-data'}

    if event['RequestType'] != 'Create':
        return {'PhysicalResourceId': 'demo-data'}

    try:
        region = os.environ.get('AWS_REGION')
        dynamodb = boto3.resource('dynamodb', region_name=region)

        # Get table names from properties
        customers_table_name = event['ResourceProperties']['CustomersTableName']
        schemas_table_name = event['ResourceProperties']['SchemasTableName']

        # Insert demo customers
        insert_demo_customers(dynamodb, customers_table_name)

        # Insert demo usecase
        insert_demo_usecase(dynamodb, schemas_table_name)

        return {'PhysicalResourceId': 'demo-data'}

    except Exception as e:
        print(f"Error: {str(e)}")
        raise


def insert_demo_customers(dynamodb, table_name):
    """Insert demo customer data"""
    table = dynamodb.Table(table_name)

    customers = [
        {
            'customer_id': 'CUST001',
            'customer_name': 'サンプル株式会社',
            'postal_code': '〒123-4567',
            'address': '東京都目黒区上目黒1-2-3 サンプルビル 6階',
            'phone': '03-1234-5679',
            'email': 'info@sample.co.jp',
            'contact_person': 'サンプル太郎'
        },
        {
            'customer_id': 'CUST002',
            'customer_name': 'テスト商事株式会社',
            'postal_code': '〒100-0001',
            'address': '東京都千代田区千代田1-1-1',
            'phone': '03-0000-0001',
            'email': 'contact@test-corp.co.jp',
            'contact_person': '田中花子'
        },
        {
            'customer_id': 'CUST003',
            'customer_name': '株式会社デモカンパニー',
            'postal_code': '〒150-0001',
            'address': '東京都渋谷区神宮前1-1-1',
            'phone': '03-9999-9999',
            'email': 'info@demo-company.jp',
            'contact_person': '山田次郎'
        }
    ]

    for customer in customers:
        table.put_item(Item=customer)
        print(f"Inserted customer: {customer['customer_id']}")


def insert_demo_usecase(dynamodb, table_name):
    """Insert demo invoice usecase"""
    table = dynamodb.Table(table_name)

    # Load demo schema from file
    with open('demo_invoice_schema.json', 'r', encoding='utf-8') as f:
        demo_schema = json.load(f)

    # Create demo usecase
    demo_usecase = {
        'schema_type': 'app',
        'name': 'demo_invoice',
        'display_name': '(demo)請求書',
        'description': 'デモ用請求書抽出ユースケース',
        'fields': demo_schema,
        'input_methods': {
            'file_upload': True,
            's3_sync': False
        },
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat()
    }

    table.put_item(Item=demo_usecase)
    print(f"Inserted demo usecase: {demo_usecase['name']}")
