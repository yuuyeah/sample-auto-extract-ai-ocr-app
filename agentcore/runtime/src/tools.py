"""Tool management for agent runtime."""

import logging
import os
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr
from strands import tool

logger = logging.getLogger(__name__)


class ToolManager:
    """Manages tools for the agent"""
    
    def __init__(self):
        region = os.environ.get('AWS_REGION')
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.customers_table_name = os.environ.get('CUSTOMERS_TABLE', '')
    
    def get_customer_search_tools(self) -> list[Any]:
        """Get customer search tools"""
        if not self.customers_table_name:
            logger.warning("CUSTOMERS_TABLE not set. Customer search tools disabled.")
            return []
        
        table = self.dynamodb.Table(self.customers_table_name)
        
        @tool
        def search_customer_by_id(customer_id: str) -> dict:
            """顧客IDで顧客情報を検索
            
            Args:
                customer_id: 顧客ID
                
            Returns:
                顧客情報（customer_id, customer_name, postal_code, address, phone, email, contact_person）
            """
            try:
                response = table.get_item(Key={'customer_id': customer_id})
                item = response.get('Item', {})
                if item:
                    logger.info(f"Found customer: {customer_id}")
                    return item
                else:
                    logger.info(f"Customer not found: {customer_id}")
                    return {}
            except Exception as e:
                logger.error(f"Error searching customer by ID: {e}")
                return {"error": str(e)}
        
        @tool
        def search_customer_by_name(customer_name: str) -> list[dict]:
            """顧客名で顧客情報を検索（部分一致）
            
            Args:
                customer_name: 顧客名
                
            Returns:
                顧客情報のリスト（各要素: customer_id, customer_name, postal_code, address, phone, email, contact_person）
            """
            try:
                response = table.scan(
                    FilterExpression=Attr('customer_name').contains(customer_name)
                )
                items = response.get('Items', [])
                logger.info(f"Found {len(items)} customers matching: {customer_name}")
                return items
            except Exception as e:
                logger.error(f"Error searching customer by name: {e}")
                return [{"error": str(e)}]
        
        return [search_customer_by_id, search_customer_by_name]
    
    def get_all_tools(self) -> list[Any]:
        """Get all available tools"""
        customer_tools = self.get_customer_search_tools()
        
        all_tools = customer_tools
        logger.info(f"Total tools loaded: {len(all_tools)}")
        
        return all_tools
