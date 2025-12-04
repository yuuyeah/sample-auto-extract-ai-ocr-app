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
    delete_image,
    update_verification_status,
    create_individual_page_record,
    update_parent_document_status,
    get_children_by_parent_id,
    determine_parent_status,
    check_and_update_parent_status,
)

from .sagemaker_repository import (
    get_inference_component_status,
    trigger_endpoint_wakeup,
)
from .job_repository import (
    get_job,
)
from .schema_repository import (
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
    "delete_image",
    "update_verification_status",
    "create_individual_page_record",
    "update_parent_document_status",
    "get_children_by_parent_id",
    "determine_parent_status",
    "check_and_update_parent_status",
    # SageMaker operations
    "get_inference_component_status",
    "trigger_endpoint_wakeup",
    # Job operations
    "get_job",
    # Schema operations
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
