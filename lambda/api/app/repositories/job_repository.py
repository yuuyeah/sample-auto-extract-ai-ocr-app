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


def create_job(job_id=None, status="processing"):
    """
    ジョブを作成する

    Args:
        job_id (str, optional): ジョブID
        status (str): ジョブステータス

    Returns:
        str: 作成されたジョブのID
    """
    if not job_id:
        job_id = str(uuid.uuid4())

    table = get_jobs_table()
    current_time = datetime.now().isoformat()

    try:
        item = {
            "id": job_id,
            "status": status,
            "created_at": current_time,
            "updated_at": current_time
        }

        table.put_item(Item=item)
        return job_id
    except Exception as e:
        logger.error(f"ジョブ作成エラー: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Database error: {str(e)}")


def update_job_status(job_id, status):
    """
    ジョブステータスを更新する

    Args:
        job_id (str): ジョブID
        status (str): 新しいステータス
    """
    table = get_jobs_table()
    current_time = datetime.now().isoformat()

    try:
        table.update_item(
            Key={"id": job_id},
            UpdateExpression="SET #status = :status, updated_at = :updated_at",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": status,
                ":updated_at": current_time
            }
        )
    except Exception as e:
        logger.error(f"ジョブステータス更新エラー: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Database error: {str(e)}")


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


def get_images_by_job_id(job_id):
    """
    ジョブIDに関連する画像を取得する

    Args:
        job_id (str): ジョブID

    Returns:
        list: 画像リスト
    """
    table = get_images_table()

    try:
        # job_id でフィルタリングするにはスキャンが必要
        # 頻繁に使用する場合は GSI を追加すべき
        response = table.scan(
            FilterExpression=Key('job_id').eq(job_id)
        )

        images = []
        for item in response.get('Items', []):
            images.append({
                "id": item.get("id"),
                "filename": item.get("filename"),
                "status": item.get("status")
            })

        return images
    except Exception as e:
        logger.error(f"ジョブ関連画像取得エラー: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Database error: {str(e)}")


def delete_jobs_by_app_name(app_name: str):
    """
    指定されたアプリ名に関連する全てのジョブデータを削除する

    Args:
        app_name (str): アプリ名

    Returns:
        bool: 削除が成功したかどうか
    """
    try:
        table = get_jobs_table()

        # アプリ名でフィルタリングしてスキャン
        response = table.scan(
            FilterExpression=Key('app_name').eq(app_name)
        )

        # 取得したジョブを削除
        deleted_count = 0
        for item in response.get('Items', []):
            table.delete_item(Key={'id': item['id']})
            deleted_count += 1

        logger.info(f"アプリ '{app_name}' に関連する {deleted_count} 件のジョブデータを削除しました")
        return True

    except Exception as e:
        logger.error(f"ジョブデータ削除エラー (app_name: {app_name}): {str(e)}")
        return False


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
