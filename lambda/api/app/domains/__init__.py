"""
Domain logic layer - Pure business logic
"""
from .extraction_engine import (
    extract_information_from_single_image_with_ocr,
    extract_information_from_multi_images_with_ocr,
    extract_information_from_multi_images_without_ocr,
    extract_information_from_single_image_without_ocr,
    get_multipage_ocr_results,
    get_s3_object_bytes,
)
from .ocr_engine import (
    perform_ocr,
    perform_ocr_single_page,
    perform_ocr_multipage,
    perform_ocr_individual_page,
    perform_ocr_single_image,
    save_multipage_ocr_result,
)
from .schema_generator import (
    generate_schema_fields_from_image,
)
from .prompts import (
    create_single_with_ocr_prompt,
    create_single_without_ocr_prompt,
    create_multi_with_ocr_prompt,
    create_multi_without_ocr_prompt,
)
from .template import (
    generate_unified_template,
    generate_json_template,
    generate_indices_template,
)

__all__ = [
    # Extraction
    "extract_information_from_single_image_with_ocr",
    "extract_information_from_multi_images_with_ocr",
    "extract_information_from_multi_images_without_ocr",
    "extract_information_from_single_image_without_ocr",
    "get_multipage_ocr_results",
    "get_s3_object_bytes",
    # OCR
    "perform_ocr",
    "perform_ocr_single_page",
    "perform_ocr_multipage",
    "perform_ocr_individual_page",
    "perform_ocr_single_image",
    "save_multipage_ocr_result",
    # Schema
    "generate_schema_fields_from_image",
    # Prompts
    "create_single_with_ocr_prompt",
    "create_single_without_ocr_prompt",
    "create_multi_with_ocr_prompt",
    "create_multi_without_ocr_prompt",
    # Template
    "generate_unified_template",
    "generate_json_template",
    "generate_indices_template",
]
