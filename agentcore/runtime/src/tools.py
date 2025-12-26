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
        
        # テーブルを事前に初期化
        if self.customers_table_name:
            self.customers_table = self.dynamodb.Table(self.customers_table_name)
        else:
            self.customers_table = None

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

    @tool
    def search_customer_by_id(self, customer_id: str) -> dict:
        """顧客IDで顧客情報を検索
        
        Args:
            customer_id: 顧客ID
            
        Returns:
            顧客情報（customer_id, customer_name, postal_code, address, phone, email, contact_person）
        """
        if not self.customers_table:
            return {"error": "CUSTOMERS_TABLE not configured"}
            
        try:
            response = self.customers_table.get_item(Key={'customer_id': customer_id})
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
    def search_customer_by_name(self, customer_name: str) -> list[dict]:
        """顧客名で顧客情報を検索（部分一致）
        
        Args:
            customer_name: 顧客名
            
        Returns:
            顧客情報のリスト（各要素: customer_id, customer_name, postal_code, address, phone, email, contact_person）
        """
        if not self.customers_table:
            return [{"error": "CUSTOMERS_TABLE not configured"}]
            
        try:
            response = self.customers_table.scan(
                FilterExpression=Attr('customer_name').contains(customer_name)
            )
            items = response.get('Items', [])
            logger.info(f"Found {len(items)} customers matching '{customer_name}'")
            return items
        except Exception as e:
            logger.error(f"Error searching customer by name: {e}")
            return [{"error": str(e)}]

    @tool
    def verify_unit_price_calculation(self, quantity: float, unit_price: float, expected_amount: float) -> dict:
        """単価計算の検算
        
        Args:
            quantity: 数量
            unit_price: 単価
            expected_amount: 期待される金額
            
        Returns:
            検算結果（is_correct: bool, calculated_amount: float, message: str）
        """
        try:
            calculated_amount = quantity * unit_price
            is_correct = abs(calculated_amount - expected_amount) < 0.01
            
            result = {
                "is_correct": is_correct,
                "calculated_amount": calculated_amount,
                "expected_amount": expected_amount,
                "quantity": quantity,
                "unit_price": unit_price
            }
            
            if is_correct:
                result["message"] = "単価計算は正しいです"
            else:
                result["message"] = f"単価計算が間違っています。{quantity} × {unit_price} = {calculated_amount}"
            
            logger.info(f"単価検算: {quantity} × {unit_price} = {calculated_amount}, 期待値: {expected_amount}, 正しい: {is_correct}")
            return result
        except Exception as e:
            logger.error(f"単価検算エラー: {e}")
            return {"error": str(e)}

    @tool
    def verify_subtotal_calculation(self, amounts: list[float], expected_subtotal: float) -> dict:
        """小計計算の検算
        
        Args:
            amounts: 金額のリスト
            expected_subtotal: 期待される小計
            
        Returns:
            検算結果（is_correct: bool, calculated_subtotal: float, message: str）
        """
        try:
            calculated_subtotal = sum(amounts)
            is_correct = abs(calculated_subtotal - expected_subtotal) < 0.01
            
            result = {
                "is_correct": is_correct,
                "calculated_subtotal": calculated_subtotal,
                "expected_subtotal": expected_subtotal,
                "amounts": amounts
            }
            
            if is_correct:
                result["message"] = "小計の計算は正しいです"
            else:
                result["message"] = f"小計が間違っています。{' + '.join(map(str, amounts))} = {calculated_subtotal}"
            
            logger.info(f"小計検算: {amounts} = {calculated_subtotal}, 期待値: {expected_subtotal}, 正しい: {is_correct}")
            return result
        except Exception as e:
            logger.error(f"小計検算エラー: {e}")
            return {"error": str(e)}

    @tool
    def verify_total_with_tax_calculation(self, subtotal: float, tax_amount: float, expected_total: float) -> dict:
        """税込み合計計算の検算
        
        Args:
            subtotal: 小計
            tax_amount: 消費税額
            expected_total: 期待される税込み合計
            
        Returns:
            検算結果（is_correct: bool, calculated_total: float, message: str）
        """
        try:
            calculated_total = subtotal + tax_amount
            is_correct = abs(calculated_total - expected_total) < 0.01
            
            result = {
                "is_correct": is_correct,
                "calculated_total": calculated_total,
                "expected_total": expected_total,
                "subtotal": subtotal,
                "tax_amount": tax_amount
            }
            
            if is_correct:
                result["message"] = "税込み合計の計算は正しいです"
            else:
                result["message"] = f"税込み合計が間違っています。{subtotal} + {tax_amount} = {calculated_total}"
            
            logger.info(f"税込み合計検算: {subtotal} + {tax_amount} = {calculated_total}, 期待値: {expected_total}, 正しい: {is_correct}")
            return result
        except Exception as e:
            logger.error(f"税込み合計検算エラー: {e}")
            return {"error": str(e)}

    @tool
    def verify_tax_calculation(self, subtotal: float, tax_rate: float, actual_tax_amount: float) -> dict:
        """消費税計算の検算
        
        Args:
            subtotal: 小計
            tax_rate: 税率（例: 0.1 for 10%）
            actual_tax_amount: 実際の消費税額
            
        Returns:
            検算結果（is_correct: bool, calculated_tax: float, message: str）
        """
        try:
            calculated_tax = subtotal * tax_rate
            is_correct = abs(calculated_tax - actual_tax_amount) < 0.01
            
            result = {
                "is_correct": is_correct,
                "calculated_tax": calculated_tax,
                "actual_tax_amount": actual_tax_amount,
                "subtotal": subtotal,
                "tax_rate": tax_rate
            }
            
            if is_correct:
                if calculated_tax != actual_tax_amount:
                    result["message"] = f"消費税の計算は正しいです（端数処理済み: 理論値{calculated_tax}円 → {actual_tax_amount}円）"
                else:
                    result["message"] = "消費税の計算は正しいです"
            else:
                result["message"] = f"消費税が間違っています。{subtotal} × {tax_rate} = {calculated_tax}"
            
            logger.info(f"消費税検算: {subtotal} × {tax_rate} = {calculated_tax}, 実際: {actual_tax_amount}, 正しい: {is_correct}")
            return result
        except Exception as e:
            logger.error(f"消費税検算エラー: {e}")
            return {"error": str(e)}

    def get_custom_tools(self) -> list[Any]:
        """Get all custom tools automatically by inspecting class methods"""
        tools = []
        
        # クラス内の全メソッドを検査してstrandsのtoolデコレータがついているものを検出
        for name in dir(self):
            if name.startswith('_'):  # プライベートメソッドをスキップ
                continue
                
            attr = getattr(self, name)
            if callable(attr) and hasattr(attr, 'tool_spec'):  # strandsのtoolデコレータがついているかチェック
                tools.append(attr)
                
        return tools

    def get_all_tools(self) -> list[Any]:
        """Get all available tools"""
        mcp_tools = self.load_mcp_tools()
        custom_tools = self.get_custom_tools()

        all_tools = mcp_tools + custom_tools
        logger.info(f"Total tools loaded: {len(all_tools)} (MCP: {len(mcp_tools)}, Custom: {len(custom_tools)})")

        return all_tools

    async def get_tool_info_for_registration(self) -> list[dict]:
        """Get tool information for DynamoDB registration"""
        tool_info = []

        # MCPツール
        mcp_tools = self.load_mcp_tools()
        for client in mcp_tools:
            try:
                async with client.session() as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    for tool in tools.tools:
                        tool_info.append({
                            'name': tool.name,
                            'description': tool.description or ''
                        })
                        logger.info(f"Found MCP tool: {tool.name}")
            except Exception as e:
                logger.error(f"Error getting MCP tool info: {e}")

        # カスタムツール（自動検出）
        custom_tools = self.get_custom_tools()
        for tool in custom_tools:
            tool_name = getattr(tool, '__name__', str(tool))
            tool_doc = getattr(tool, '__doc__', '') or ''
            description = tool_doc.strip().split('\n')[0] if tool_doc else ''
            tool_info.append({
                'name': tool_name,
                'description': description
            })
            logger.info(f"Found custom tool: {tool_name}")

        return tool_info
