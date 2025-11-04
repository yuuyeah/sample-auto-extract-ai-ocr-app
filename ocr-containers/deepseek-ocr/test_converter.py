#!/usr/bin/env python3
"""
Test script for DeepSeek to PaddleOCR schema converter
"""
import json
from model_handler import convert_deepseek_to_paddle_schema

# Sample DeepSeek OCR output (from /Users/sabamiso/Downloads/out/result_ori.md)
SAMPLE_DEEPSEEK_OUTPUT = """<|ref|>table<|/ref|><|det|>[[40, 55, 963, 135]]<|/det|>
<table><tr><td>氏名</td><td>日本</td><td>花子</td><td>昭和61年</td><td>5月</td><td>1日生</td></tr></table>

<|ref|>table<|/ref|><|det|>[[40, 200, 700, 920]]<|/det|>
<table><tr><td>住所</td><td colspan="2">東京都千代田区霞が関2-1-2</td></tr><tr><td>交付</td><td colspan="2">令和01年05月07日 12345</td></tr><tr><td colspan="3">2024年(令和06年)06月01日まで有効</td></tr><tr><td>免許の<br/>条件等</td><td colspan="2">眼鏡等</td></tr><tr><td>優良</td><td colspan="2">見本</td></tr><tr><td>番号</td><td>第 012345678900</td><td>号</td></tr><tr><td>二小原</td><td>平成15年04月01日</td><td>種</td><td>大型</td><td>中型</td><td>大特</td><td>大直</td><td>普直</td></tr><tr><td>他</td><td>平成17年06月01日</td><td>種</td><td>小型</td><td>原付</td><td>大中</td><td>普二</td><td>大特</td></tr><tr><td>二種</td><td>平成29年08月01日</td><td>類</td><td></td><td></td><td></td><td></td><td></td></tr></table>

<|ref|>image<|/ref|><|det|>[[655, 300, 955, 920]]<|/det|>"""

# Expected PaddleOCR format
EXPECTED_PADDLE_FORMAT = {
    "words": [
        {
            "id": 0,
            "content": "氏名 日本 花子 昭和61年 5月 1日生",
            "rec_score": 1.0,
            "points": [[40, 55], [963, 55], [963, 135], [40, 135]]
        },
        {
            "id": 1,
            "content": "住所 東京都千代田区霞が関2-1-2 交付 令和01年05月07日 12345...",
            "rec_score": 1.0,
            "points": [[40, 200], [700, 200], [700, 920], [40, 920]]
        }
    ]
}

def test_conversion():
    """Test the conversion function"""
    print("=" * 80)
    print("Testing DeepSeek to PaddleOCR Schema Conversion")
    print("=" * 80)
    
    # Test with sample image dimensions (1000x1000 for simplicity)
    image_width = 1000
    image_height = 1000
    
    print(f"\nImage dimensions: {image_width}x{image_height}")
    print(f"\nInput (DeepSeek format):\n{SAMPLE_DEEPSEEK_OUTPUT[:200]}...\n")
    
    # Convert
    result = convert_deepseek_to_paddle_schema(
        SAMPLE_DEEPSEEK_OUTPUT,
        image_width,
        image_height
    )
    
    # Display results
    print("=" * 80)
    print("Conversion Results")
    print("=" * 80)
    print(f"\nTotal words detected: {len(result['words'])}")
    
    for i, word in enumerate(result['words']):
        print(f"\n--- Word {i} ---")
        print(f"ID: {word['id']}")
        print(f"Content: {word['content'][:100]}{'...' if len(word['content']) > 100 else ''}")
        print(f"Rec Score: {word['rec_score']}")
        print(f"Points: {word['points']}")
    
    # Validate schema
    print("\n" + "=" * 80)
    print("Schema Validation")
    print("=" * 80)
    
    assert "words" in result, "Missing 'words' key"
    assert isinstance(result["words"], list), "'words' should be a list"
    
    for word in result["words"]:
        assert "id" in word, "Missing 'id' in word"
        assert "content" in word, "Missing 'content' in word"
        assert "rec_score" in word, "Missing 'rec_score' in word"
        assert "points" in word, "Missing 'points' in word"
        assert isinstance(word["points"], list), "'points' should be a list"
        assert len(word["points"]) == 4, "'points' should have 4 coordinates"
        for point in word["points"]:
            assert len(point) == 2, "Each point should have 2 values (x, y)"
    
    print("✅ All schema validations passed!")
    
    # Output JSON
    print("\n" + "=" * 80)
    print("Final JSON Output")
    print("=" * 80)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    return result

if __name__ == "__main__":
    try:
        result = test_conversion()
        print("\n" + "=" * 80)
        print("✅ TEST PASSED")
        print("=" * 80)
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
