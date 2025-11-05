"""Tool management for agent runtime."""

import json
import logging
import os
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr
from mcp import StdioServerParameters, stdio_client
from strands import tool
from strands.tools.mcp import MCPClient

from .config import get_uv_environment

logger = logging.getLogger(__name__)


class ToolManager:
    """Manages tools for the agent"""
    
    def __init__(self):
        region = os.environ.get('AWS_REGION')
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.customers_table_name = os.environ.get('CUSTOMERS_TABLE', '')
        self.mcp_tools = None
    
    def load_mcp_tools(self) -> list[Any]:
        """Load MCP tools from mcp.json"""
        if self.mcp_tools is not None:
            return self.mcp_tools

        try:
            with open("mcp.json") as f:
                mcp_json = json.loads(f.read())

                if "mcpServers" not in mcp_json:
                    logger.warning("mcpServers not defined in mcp.json")
                    self.mcp_tools = []
                    return self.mcp_tools

                mcp_servers = mcp_json["mcpServers"]
                mcp_clients = []
                uv_env = get_uv_environment()

                for server_name, server in mcp_servers.items():
                    try:
                        client = MCPClient(
                            lambda server=server: stdio_client(
                                StdioServerParameters(
                                    command=server["command"],
                                    args=server.get("args", []),
                                    env={**uv_env, **server.get("env", {})},
                                )
                            )
                        )
                        mcp_clients.append(client)
                        logger.info(f"Loaded MCP server: {server_name}")
                    except Exception as e:
                        logger.error(f"Failed to load MCP server {server_name}: {e}")

                self.mcp_tools = mcp_clients
                return self.mcp_tools
        except FileNotFoundError:
            logger.info("mcp.json not found. Skipping MCP tools.")
            self.mcp_tools = []
            return self.mcp_tools
        except Exception as e:
            logger.error(f"Error loading MCP tools: {e}")
            self.mcp_tools = []
            return self.mcp_tools
    
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
    
    def get_calculation_verification_tools(self) -> list[Any]:
        """Get calculation verification tools"""
        
        @tool
        def verify_unit_price_calculation(
            quantity: float,
            unit_price: float,
            actual_amount: float,
            tolerance: float = 0.01
        ) -> dict:
            """単価×個数の計算を検証
            
            Args:
                quantity: 数量
                unit_price: 単価
                actual_amount: 実際の金額
                tolerance: 許容誤差（デフォルト0.01）
                
            Returns:
                検証結果 {"is_correct": bool, "calculated_amount": float, "difference": float, "message": str}
            """
            try:
                calculated_amount = quantity * unit_price
                difference = abs(calculated_amount - actual_amount)
                is_correct = difference <= tolerance
                
                result = {
                    "is_correct": is_correct,
                    "calculated_amount": calculated_amount,
                    "actual_amount": actual_amount,
                    "difference": difference,
                    "calculation": f"{quantity} × {unit_price} = {calculated_amount}"
                }
                
                if is_correct:
                    result["message"] = "計算は正しいです"
                else:
                    result["message"] = f"計算が間違っています。{quantity} × {unit_price} = {calculated_amount}"
                
                logger.info(f"単価×個数検算: {quantity} × {unit_price} = {calculated_amount}, 実際: {actual_amount}, 正しい: {is_correct}")
                return result
                
            except Exception as e:
                logger.error(f"単価×個数検算エラー: {e}")
                return {"error": str(e)}
        
        @tool
        def verify_subtotal_calculation(
            amounts: list[float],
            actual_subtotal: float,
            tolerance: float = 0.01
        ) -> dict:
            """各項目の合計と小計の計算を検証
            
            Args:
                amounts: 各項目の金額のリスト
                actual_subtotal: 実際の小計
                tolerance: 許容誤差（デフォルト0.01）
                
            Returns:
                検証結果 {"is_correct": bool, "calculated_subtotal": float, "difference": float, "message": str}
            """
            try:
                calculated_subtotal = sum(amounts)
                difference = abs(calculated_subtotal - actual_subtotal)
                is_correct = difference <= tolerance
                
                result = {
                    "is_correct": is_correct,
                    "calculated_subtotal": calculated_subtotal,
                    "actual_subtotal": actual_subtotal,
                    "difference": difference,
                    "calculation": " + ".join([str(amount) for amount in amounts]) + f" = {calculated_subtotal}"
                }
                
                if is_correct:
                    result["message"] = "小計の計算は正しいです"
                else:
                    result["message"] = f"小計が間違っています。各項目の合計: {calculated_subtotal}"
                
                logger.info(f"小計検算: {amounts} の合計 = {calculated_subtotal}, 実際: {actual_subtotal}, 正しい: {is_correct}")
                return result
                
            except Exception as e:
                logger.error(f"小計検算エラー: {e}")
                return {"error": str(e)}
        
        @tool
        def verify_total_with_tax_calculation(
            subtotal: float,
            tax_amount: float,
            actual_total: float,
            tolerance: float = 0.01
        ) -> dict:
            """小計+消費税と総額の計算を検証
            
            Args:
                subtotal: 小計
                tax_amount: 消費税額
                actual_total: 実際の総額
                tolerance: 許容誤差（デフォルト0.01）
                
            Returns:
                検証結果 {"is_correct": bool, "calculated_total": float, "difference": float, "message": str}
            """
            try:
                calculated_total = subtotal + tax_amount
                difference = abs(calculated_total - actual_total)
                is_correct = difference <= tolerance
                
                result = {
                    "is_correct": is_correct,
                    "calculated_total": calculated_total,
                    "actual_total": actual_total,
                    "difference": difference,
                    "calculation": f"{subtotal} + {tax_amount} = {calculated_total}"
                }
                
                if is_correct:
                    result["message"] = "総額の計算は正しいです"
                else:
                    result["message"] = f"総額が間違っています。{subtotal} + {tax_amount} = {calculated_total}"
                
                logger.info(f"総額検算: {subtotal} + {tax_amount} = {calculated_total}, 実際: {actual_total}, 正しい: {is_correct}")
                return result
                
            except Exception as e:
                logger.error(f"総額検算エラー: {e}")
                return {"error": str(e)}
        
        return [
            verify_unit_price_calculation,
            verify_subtotal_calculation,
            verify_total_with_tax_calculation
        ]
    
    def get_all_tools(self) -> list[Any]:
        """Get all available tools"""
        mcp_tools = self.load_mcp_tools()
        customer_tools = self.get_customer_search_tools()
        calculation_tools = self.get_calculation_verification_tools()
        
        all_tools = mcp_tools + customer_tools + calculation_tools
        logger.info(f"Total tools loaded: {len(all_tools)} (MCP: {len(mcp_tools)}, Custom: {len(customer_tools)}, Calculation: {len(calculation_tools)})")
        
        return all_tools
    
    def get_tool_info_for_registration(self) -> list[dict]:
        """Get tool information for DynamoDB registration"""
        tool_info = []
        
        # MCPツール
        mcp_tools = self.load_mcp_tools()
        for client in mcp_tools:
            try:
                if hasattr(client, 'list_tools_sync'):
                    tools = client.list_tools_sync()
                    for tool in tools:
                        tool_name = tool.tool_spec['name']
                        description = tool.tool_spec.get('description', '')
                        tool_info.append({
                            'name': tool_name,
                            'description': description
                        })
                        logger.info(f"Found MCP tool: {tool_name}")
            except Exception as e:
                logger.error(f"Error getting MCP tool info: {e}")
        
        # カスタムツール
        custom_tools = self.get_customer_search_tools()
        for tool in custom_tools:
            tool_name = getattr(tool, '__name__', str(tool))
            tool_doc = getattr(tool, '__doc__', '') or ''
            description = tool_doc.strip().split('\n')[0] if tool_doc else ''
            tool_info.append({
                'name': tool_name,
                'description': description
            })
            logger.info(f"Found custom tool: {tool_name}")
        
        # 検算ツール
        calculation_tools = self.get_calculation_verification_tools()
        for tool in calculation_tools:
            tool_name = getattr(tool, '__name__', str(tool))
            tool_doc = getattr(tool, '__doc__', '') or ''
            description = tool_doc.strip().split('\n')[0] if tool_doc else ''
            tool_info.append({
                'name': tool_name,
                'description': description
            })
            logger.info(f"Found calculation tool: {tool_name}")
        
        return tool_info
