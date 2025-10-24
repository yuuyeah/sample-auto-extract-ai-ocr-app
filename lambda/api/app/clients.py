"""
共通のAWSクライアント設定
"""
import json
import logging
import uuid
import boto3
from botocore.config import Config
from config import settings

logger = logging.getLogger(__name__)


def create_s3_client():
    """
    リージョン固定・バケット仮想ホスト名対応のS3クライアントを作成
    """
    return boto3.client(
        's3',
        region_name=settings.AWS_REGION,
        config=Config(
            signature_version='s3v4',
            s3={
                'addressing_style': 'virtual'  # バケット仮想ホスト名を使用
            }
        )
    )


def create_bedrock_client(region_name=None):
    """
    Bedrock Runtime クライアントを作成
    
    Args:
        region_name (str, optional): リージョン名。未指定時はsettings.MODEL_REGIONを使用
    """
    return boto3.client(
        'bedrock-runtime',
        region_name=region_name or settings.MODEL_REGION,
        config=Config(
            read_timeout=900,  # 15分のタイムアウト
            retries={'max_attempts': 3}
        )
    )


def create_dynamodb_client():
    """
    DynamoDB クライアントを作成
    """
    return boto3.client(
        'dynamodb',
        region_name=settings.AWS_REGION
    )


def create_sagemaker_runtime_client():
    """
    SageMaker Runtime クライアントを作成
    """
    return boto3.client(
        'runtime.sagemaker',
        region_name=settings.AWS_REGION
    )


def create_bedrock_agentcore_client():
    """
    Bedrock AgentCore クライアントを作成
    """
    return boto3.client(
        'bedrock-agentcore',
        region_name=settings.AWS_REGION,
        config=Config(
            read_timeout=300,
            retries={'max_attempts': 3}
        )
    )


def create_dynamodb_resource():
    """
    DynamoDB リソースを作成
    """
    return boto3.resource(
        'dynamodb',
        region_name=settings.AWS_REGION
    )


# グローバルクライアントインスタンス
s3_client = create_s3_client()
bedrock_client = create_bedrock_client()
dynamodb_client = create_dynamodb_client()
dynamodb_resource = create_dynamodb_resource()
sagemaker_runtime_client = create_sagemaker_runtime_client()
bedrock_agentcore_client = create_bedrock_agentcore_client()


class AgentClient:
    """Client for calling AgentCore Runtime"""
    
    def __init__(self):
        self.runtime_arn = settings.AGENT_RUNTIME_ARN
        self.client = bedrock_agentcore_client
        self.dynamodb = dynamodb_resource
    
    async def get_tools(self) -> list:
        """Get available tools from DynamoDB
        
        Returns:
            List of available tools
        """
        try:
            tools_table_name = settings.TOOLS_TABLE_NAME
            if not tools_table_name:
                logger.warning("TOOLS_TABLE_NAME not set")
                return []
            
            table = self.dynamodb.Table(tools_table_name)
            response = table.scan()
            
            items = response.get('Items', [])
            tools = [
                {
                    "name": item.get("tool_name", ""),
                    "description": item.get("description", "")
                }
                for item in items
            ]
            
            logger.info(f"Retrieved {len(tools)} tools from DynamoDB")
            return tools
        
        except Exception as e:
            logger.error(f"Error getting tools from DynamoDB: {e}")
            return []
    
    async def invoke_agent(
        self,
        messages: list,
        system_prompt: str,
        prompt: str,
        model_info: dict
    ) -> str:
        """Invoke AgentCore Runtime and return response text
        
        Args:
            messages: Conversation history
            system_prompt: System prompt
            prompt: User prompt
            model_info: Model configuration
            
        Returns:
            Agent response text
        """
        try:
            payload = json.dumps({
                "input": {
                    "messages": messages,
                    "system_prompt": system_prompt,
                    "prompt": prompt,
                    "model": model_info
                }
            })
            
            session_id = str(uuid.uuid4()).replace('-', '') + str(uuid.uuid4()).replace('-', '')[:1]
            
            response = self.client.invoke_agent_runtime(
                agentRuntimeArn=self.runtime_arn,
                runtimeSessionId=session_id,
                payload=payload
            )
            
            response_body = response['response'].read()
            response_data = json.loads(response_body)
            
            return self._parse_response(response_data)
        
        except Exception as e:
            logger.error(f"Error invoking agent: {e}")
            raise
    
    def _parse_response(self, response_data: dict) -> str:
        """Parse AgentCore Runtime response
        
        Args:
            response_data: Response data from invoke_agent_runtime
            
        Returns:
            Extracted text from response
        """
        try:
            # Expected format: {"output": {"result": {"message": {"role": "assistant", "content": [{"text": "..."}]}}}}
            if isinstance(response_data, dict):
                output = response_data.get("output", {})
                result = output.get("result", {})
                message = result.get("message", {})
                
                if isinstance(message, dict):
                    content = message.get("content", [])
                    if isinstance(content, list) and len(content) > 0:
                        # Extract text from first content block
                        first_content = content[0]
                        if isinstance(first_content, dict):
                            return first_content.get("text", "")
                
                # Fallback to string representation
                if "output" in response_data:
                    return str(output)
                elif "result" in response_data:
                    return str(result)
            
            return str(response_data)
        
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            logger.error(f"Response data: {response_data}")
            return f"Error parsing response: {str(e)}"
