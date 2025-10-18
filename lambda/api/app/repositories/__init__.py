"""
Data access layer for DynamoDB operations
"""
from .image_repository import (
    create_image_record,
    get_images,
    get_image,
    update_image_status,
    update_ocr_result,
    update_extracted_info,
    update_converted_image,
    delete_images_by_app_name,
    create_individual_page_record,
    update_parent_document_status,
    get_children_by_parent_id,
    determine_parent_status,
    check_and_update_parent_status,
)
from .job_repository import (
    create_job,
    get_job,
    update_job_status,
    get_images_by_job_id,
    delete_jobs_by_app_name,
)
from .schema_repository import (
    DEFAULT_APP,
    load_app_schemas,
    get_app_schemas,
    get_app_schema,
    get_extraction_fields_for_app,
    get_field_names_for_app,
    get_app_display_name,
    get_app_input_methods,
    get_custom_prompt_for_app,
    update_app_schema,
    delete_app_schema,
)

__all__ = [
    # Image operations
    "create_image_record",
    "get_images",
    "get_image",
    "update_image_status",
    "update_ocr_result",
    "update_extracted_info",
    "update_converted_image",
    "delete_images_by_app_name",
    "create_individual_page_record",
    "update_parent_document_status",
    "get_children_by_parent_id",
    "determine_parent_status",
    "check_and_update_parent_status",
    # Job operations
    "create_job",
    "get_job",
    "update_job_status",
    "get_images_by_job_id",
    "delete_jobs_by_app_name",
    # Schema operations
    "DEFAULT_APP",
    "load_app_schemas",
    "get_app_schemas",
    "get_app_schema",
    "get_extraction_fields_for_app",
    "get_field_names_for_app",
    "get_app_display_name",
    "get_app_input_methods",
    "get_custom_prompt_for_app",
    "update_app_schema",
    "delete_app_schema",
]
