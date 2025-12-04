from clients import dynamodb_resource
import logging
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from fastapi import HTTPException
from datetime import datetime
import uuid
from config import settings

logger = logging.getLogger(__name__)


def get_jobs_table():
    """
    ジョブテーブルのリソースを取得する

    Returns:
        boto3.resources.factory.dynamodb_resource.Table: DynamoDB テーブルリソース
    """
    table_name = settings.JOBS_TABLE_NAME
    if not table_name:
        logger.error("JOBS_TABLE_NAME 環境変数が設定されていません")
        raise HTTPException(
            status_code=500, detail="Database configuration error")

    return dynamodb_resource.Table(table_name)


def get_images_table():
    """
    画像テーブルのリソースを取得する（job_repository内で使用）

    Returns:
        boto3.resources.factory.dynamodb_resource.Table: DynamoDB テーブルリソース
    """
    table_name = settings.IMAGES_TABLE_NAME
    if not table_name:
        logger.error("IMAGES_TABLE_NAME 環境変数が設定されていません")
        raise HTTPException(
            status_code=500, detail="Database configuration error")

    return dynamodb_resource.Table(table_name)


def get_job(job_id):
    """
    ジョブ情報を取得する

    Args:
        job_id (str): ジョブID

    Returns:
        dict: ジョブ情報
    """
    table = get_jobs_table()

    try:
        response = table.get_item(Key={"id": job_id})
        item = response.get("Item")

        if not item:
            raise HTTPException(status_code=404, detail="Job not found")

        return item
    except ClientError as e:
        logger.error(f"ジョブ取得エラー: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Database error: {str(e)}")


def create_agent_job(image_id: str):
    """Create agent correction job

    Args:
        image_id: Image ID

    Returns:
        str: Job ID
    """
    job_id = str(uuid.uuid4())
    table = get_jobs_table()
    current_time = datetime.now().isoformat()

    try:
        item = {
            "id": job_id,
            "image_id": image_id,
            "job_type": "agent_correction",
            "status": "processing",
            "created_at": current_time,
            "updated_at": current_time
        }
        table.put_item(Item=item)
        return job_id
    except Exception as e:
        logger.error(f"Error creating agent job: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Database error: {str(e)}")


def update_agent_job(job_id: str, status: str, suggestions: list = None, error: str = None):
    """Update agent correction job

    Args:
        job_id: Job ID
        status: Job status (processing, completed, failed)
        suggestions: Correction suggestions
        error: Error message if failed
    """
    table = get_jobs_table()
    current_time = datetime.now().isoformat()

    try:
        update_expr = "SET #status = :status, updated_at = :updated_at"
        expr_attr_names = {"#status": "status"}
        expr_attr_values = {
            ":status": status,
            ":updated_at": current_time
        }

        if status == "completed":
            update_expr += ", completed_at = :completed_at"
            expr_attr_values[":completed_at"] = current_time

            if suggestions is not None:
                update_expr += ", suggestions = :suggestions"
                expr_attr_values[":suggestions"] = suggestions

        if error:
            update_expr += ", #error = :error"
            expr_attr_names["#error"] = "error"
            expr_attr_values[":error"] = error

        table.update_item(
            Key={"id": job_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values
        )
    except Exception as e:
        logger.error(f"Error updating agent job: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Database error: {str(e)}")
