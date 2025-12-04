"""
SageMaker エンドポイント管理リポジトリ
"""
import logging
from clients import sagemaker_client, sagemaker_runtime_client
from config import settings

logger = logging.getLogger(__name__)


def get_inference_component_status() -> dict:
    """
    推論コンポーネントの状態を取得

    Returns:
        dict: {
            'ready': bool,
            'copy_count': int,
            'status': str
        }
    """
    try:
        response = sagemaker_client.describe_inference_component(
            InferenceComponentName=settings.SAGEMAKER_INFERENCE_COMPONENT_NAME
        )

        copy_count = response['RuntimeConfig']['CurrentCopyCount']

        return {
            'ready': copy_count > 0,
            'copy_count': copy_count,
            'status': 'ready' if copy_count > 0 else 'cold'
        }
    except Exception as e:
        logger.error(f"Error getting inference component status: {str(e)}")
        raise


def trigger_endpoint_wakeup():
    """
    エンドポイントのスケールアウトをトリガー（ダミーリクエスト送信）
    """
    try:
        sagemaker_runtime_client.invoke_endpoint(
            EndpointName=settings.SAGEMAKER_ENDPOINT_NAME,
            InferenceComponentName=settings.SAGEMAKER_INFERENCE_COMPONENT_NAME,
            Body='{"dummy": true}',
            ContentType='application/json'
        )
    except Exception as e:
        # NoCapacityエラーが期待される（これがスケールアウトをトリガー）
        logger.info(f"Triggered endpoint wakeup (expected error): {str(e)}")
