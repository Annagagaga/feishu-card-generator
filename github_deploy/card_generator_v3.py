import copy
import re


def generate_card_from_template(template, extracted_list):
    card = copy.deepcopy(template)

    if not card.get('dsl', {}).get('body', {}).get('elements'):
        print('模版格式异常，返回原始模版')
        return card

    elements = card['dsl']['body']['elements']

    category_prefix_map = {
        '重点能力': 'key',
        '通用能力': 'common',
        '搜索能力': 'search',
        '推荐能力': 'recommend',
        '对话能力': 'chat'
    }

    icon_map = {
        '重点能力': '🔥',
        '通用能力': '🧩',
        '搜索能力': '🎯',
        '推荐能力': '🏷️',
        '对话能力': '💬'
    }

    category_count = {
        '重点能力': 0,
        '通用能力': 0,
        '搜索能力': 0,
        '推荐能力': 0,
        '对话能力': 0
    }

    max_modules = 3

    for extracted_data in extracted_list:
        category = extracted_data.get('category', '通用能力')
        if category not in category_count:
            category = '通用能力'
        
        if category_count[category] >= max_modules:
            print(f'跳过 {category} 第 {category_count[category]+1} 个，已达到上限 {max_modules}')
            continue

        prefix = category_prefix_map.get(category, 'common')
        count = category_count[category] + 1
        target_title_id = f'{prefix}_{count}_title'
        target_body_id = f'{prefix}_{count}_body'
        target_picture_id = f'{prefix}_{count}_picture'

        title = extracted_data.get('title', '功能更新')
        content = extracted_data.get('content', '')
        img_key = extracted_data.get('img_key', '')
        icon = icon_map.get(category, '🧩')

        found = False

        for element in elements:
            if element.get('tag') == 'column_set':
                for column in element.get('columns', []):
                    column_elements = column.get('elements', [])
                    
                    title_element = None
                    body_element = None
                    picture_element = None
                    
                    for el in column_elements:
                        element_id = el.get('element_id', '')
                        if element_id == target_title_id:
                            title_element = el
                        elif element_id == target_body_id:
                            body_element = el
                        elif element_id == target_picture_id:
                            picture_element = el
                    
                    if title_element and body_element:
                        found = True
                        old_content = title_element.get('content', '')
                        # 保留原有的颜色配置
                        match = re.search(r"(<font[^>]*>).*?(</font>)", old_content, flags=re.IGNORECASE)
                        if match:
                            title_element['content'] = f"**{match.group(1)}{icon} {title}{match.group(2)}**"
                        else:
                            title_element['content'] = f"**{icon} {title}**"
                        body_element['content'] = content
                        
                        if picture_element:
                            if img_key:
                                picture_element['img_key'] = img_key
                            else:
                                # 如果没有上传新图片，可以选择移除图片组件，也可以保留模板默认的
                                column_elements.remove(picture_element)
                        break
            
            if found:
                break

        if found:
            category_count[category] += 1
            print(f'✓ 已填充 {category} 第 {count} 个: {title}')
        else:
            print(f'✗ 未找到 {target_title_id}，跳过: {title}')

    # --- 第三步：清理未使用的板块 ---
    elements_to_keep = []
    for element in elements:
        keep = True
        element_id = element.get('element_id', '')
        
        # 1. 检查是否是需要删除的分类大标题或分割线 (整个分类都为空时)
        for category, prefix in category_prefix_map.items():
            if category_count[category] == 0:
                if element_id == f'title_{prefix}':
                    keep = False
                if element_id == f'{prefix}_end':
                    keep = False
                    
        # 2. 检查是否是需要删除的空白 Item Column Set
        if element.get('tag') == 'column_set':
            for column in element.get('columns', []):
                col_id = column.get('element_id', '')
                for category, prefix in category_prefix_map.items():
                    count = category_count[category]
                    # 如果该分类只填了 count 个，那么 count+1 到 max_modules 的空壳都要删掉
                    for i in range(count + 1, max_modules + 1):
                        if col_id == f'section_{prefix}_{i}':
                            keep = False
                            break
                if not keep:
                    break
        
        if keep:
            elements_to_keep.append(element)
            
    card['dsl']['body']['elements'] = elements_to_keep

    return card
