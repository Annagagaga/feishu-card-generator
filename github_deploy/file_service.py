import json
import os


def save_extracted_texts(texts, output_path):
    try:
        full_path = os.path.abspath(output_path)
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(texts, f, ensure_ascii=False, indent=2)
        print(f"文案已保存到: {full_path}")
        return full_path
    except Exception as e:
        print(f"保存文案失败: {str(e)}")
        raise


def load_extracted_texts(input_path):
    try:
        full_path = os.path.abspath(input_path)
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载文案失败: {str(e)}")
        raise


def save_card(card, output_path):
    try:
        full_path = os.path.abspath(output_path)
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(card, f, ensure_ascii=False, indent=2)
        print(f"卡片已保存到: {full_path}")
        return full_path
    except Exception as e:
        print(f"保存卡片失败: {str(e)}")
        raise


def load_template(template_path):
    try:
        full_path = os.path.abspath(template_path)
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载模版失败: {str(e)}")
        raise
