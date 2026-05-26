import os
import subprocess
import json
import requests
import re

def get_tenant_access_token():
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise Exception("未配置 FEISHU_APP_ID 或 FEISHU_APP_SECRET")
        
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": app_id,
        "app_secret": app_secret
    }
    response = requests.post(url, json=payload)
    data = response.json()
    if data.get("code") != 0:
        raise Exception(f"获取 tenant_access_token 失败: {data.get('msg')}")
    return data.get("tenant_access_token")

def upload_image_to_feishu(file_bytes):
    token = get_tenant_access_token()
    url = "https://open.feishu.cn/open-apis/im/v1/images"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    files = {
        "image": file_bytes
    }
    data = {
        "image_type": "message"
    }
    response = requests.post(url, headers=headers, files=files, data=data)
    result = response.json()
    if result.get("code") != 0:
        raise Exception(f"上传图片失败: {result.get('msg')} (code: {result.get('code')})")
    return result.get("data", {}).get("image_key")

def get_doc_content(doc_url):
    print(f"正在使用飞书原生 API 获取文档内容...")
    
    # 提取 doc_token
    # 支持多种格式的飞书文档 URL
    doc_token = None
    
    # 尝试匹配 wiki 链接 (如 https://bytedance.larkoffice.com/wiki/QWnLwgCo3ihjIek5GBacdwhqnsc)
    wiki_match = re.search(r'wiki/([a-zA-Z0-9]+)', doc_url)
    if wiki_match:
        wiki_token = wiki_match.group(1)
        # 获取 wiki 对应的真实节点信息
        try:
            token = get_tenant_access_token()
            url = f"https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node?token={wiki_token}"
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(url, headers=headers)
            result = response.json()
            if result.get("code") == 0:
                doc_token = result.get("data", {}).get("node", {}).get("obj_token")
            else:
                print(f"获取 wiki 节点失败: {result.get('msg')}，尝试直接使用该 token")
                doc_token = wiki_token
        except Exception as e:
            print(f"解析 wiki 链接出错: {e}")
            doc_token = wiki_token
            
    # 尝试匹配 docx 链接
    if not doc_token:
        docx_match = re.search(r'docx/([a-zA-Z0-9]+)', doc_url)
        if docx_match:
            doc_token = docx_match.group(1)
            
    # 尝试匹配 doc 链接 (旧版)
    if not doc_token:
        doc_match = re.search(r'doc/([a-zA-Z0-9]+)', doc_url)
        if doc_match:
            doc_token = doc_match.group(1)

    if not doc_token:
        # 如果正则没匹配上，尝试把整个 URL 作为 token (可能是直接传了 token)
        if "http" not in doc_url:
            doc_token = doc_url
        else:
            raise Exception("无法从链接中解析出有效的文档 Token，请确保链接格式正确")

    print(f"解析到文档 Token: {doc_token}")
    
    try:
        token = get_tenant_access_token()
        # 调用获取文档所有块的接口
        url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/blocks"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.get(url, headers=headers)
        result = response.json()
        
        if result.get("code") != 0:
            error_msg = result.get("msg", "")
            if result.get("code") == 99991663 or "not found" in error_msg.lower() or "permission" in error_msg.lower():
                raise Exception(f"没有权限访问该文档。请确保已将该飞书文档通过右上角【分享】给机器人应用 (应用名: 你的自建应用)！(错误码: {result.get('code')})")
            raise Exception(f"API 请求失败: {error_msg} (code: {result.get('code')})")
            
        items = result.get("data", {}).get("items", [])
        text_content = ""
        
        for block in items:
            block_type = block.get("block_type")
            # 处理各种包含文本的块类型
            if block_type in [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15]:
                # 不同的块类型其内容存储在不同的字段中
                # 根据飞书 API 文档，文本内容通常在对应类型的对象下的 elements 里
                type_map = {
                    1: "page", 2: "text", 3: "heading1", 4: "heading2", 
                    5: "heading3", 6: "heading4", 7: "heading5", 8: "heading6",
                    9: "heading7", 11: "bullet", 12: "ordered", 13: "code",
                    14: "quote", 15: "equation"
                }
                
                type_key = type_map.get(block_type)
                if type_key and type_key in block:
                    elements = block[type_key].get("elements", [])
                    for element in elements:
                        text_run = element.get("text_run", {})
                        if text_run:
                            text_content += text_run.get("content", "")
                    text_content += "\n"
                    
        print(f"✓ 成功通过 API 获取文档内容，共 {len(text_content)} 字符")
        return text_content
        
    except Exception as e:
        print(f"获取文档内容失败: {e}")
        raise Exception(f"获取文档内容失败: {str(e)}")

def print_setup_guide():
    print("\n" + "="*60)
    print("📋 飞书 CLI 已配置")
    print("="*60)
    print("已使用您的个人账号进行授权。")
    print("="*60 + "\n")
