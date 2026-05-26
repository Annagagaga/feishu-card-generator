import streamlit as st
import os
import json
from dotenv import load_dotenv

from llm_service import extract_text_from_prd, refine_text_with_ai, translate_to_english
from feishu_service_v2 import get_doc_content, upload_image_to_feishu
from file_service import save_card, load_template
from card_generator_v3 import generate_card_from_template

load_dotenv()

st.set_page_config(page_title="飞书功能卡片生成器", page_icon="🚀", layout="wide")

st.title("🚀 飞书功能发布卡片生成器")
st.markdown("通过输入飞书 PRD 文档链接或文本，自动提取业务价值并生成飞书发布卡片。")

if "extracted_list" not in st.session_state:
    st.session_state.extracted_list = []
if "processed_inputs" not in st.session_state:
    st.session_state.processed_inputs = set()

def _template_path(file_name: str) -> str:
    return os.path.join(os.path.dirname(__file__), file_name)

st.header("1. 输入 PRD 内容或链接")
st.markdown("一个输入框对应一个飞书文档链接或一段纯文本。点击 **➕ 新增输入框** 可以继续添加。")

# 处理提取逻辑的核心函数
def process_extraction(input_list):
    valid_parts = [p.strip() for p in input_list if p.strip()]
    if not valid_parts:
        st.warning("请输入有效内容或链接")
        return [], []
        
    new_extracted = []
    success_parts = []
    failed_parts = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    has_error = False
    for i, part in enumerate(valid_parts):
        is_link = part.startswith("http") and "larkoffice.com" in part and len(part.split()) == 1
        
        if is_link:
            status_text.text(f"正在读取文档 {i+1}/{len(valid_parts)}: {part}")
            try:
                content = get_doc_content(part)
                status_text.text(f"正在提取文档 {i+1}/{len(valid_parts)} 的文案...")
                extracted = extract_text_from_prd(content)
                extracted["source"] = part
                new_extracted.append(extracted)
                success_parts.append(part)
            except Exception as e:
                st.error(f"处理链接 {part} 失败: {e}")
                has_error = True
                failed_parts.append(part)
        else:
            status_text.text(f"正在提取文本 {i+1}/{len(valid_parts)} 的文案...")
            try:
                extracted = extract_text_from_prd(part)
                source_preview = part[:20].replace('\n', ' ') + "..."
                extracted["source"] = f"文本: {source_preview}"
                new_extracted.append(extracted)
                success_parts.append(part)
            except Exception as e:
                st.error(f"处理文本失败: {e}")
                has_error = True
                failed_parts.append(part)
                
        progress_bar.progress((i + 1) / len(valid_parts))
    
    # 统一使用 extend 进行追加，避免覆盖老数据
    if new_extracted:
        st.session_state.extracted_list.extend(new_extracted)
        st.session_state.card_generated = False
        status_text.text("✅ 提取完成！已追加到下方项目列表中。")
        
    if has_error:
        status_text.text("⚠️ 部分内容提取失败，请根据上方报错信息处理后重试。")
    return success_parts, failed_parts

if "input_boxes" not in st.session_state:
    st.session_state.input_boxes = [""]

# 渲染输入框：仅通过“➕ 新增输入框”按钮显式新增，避免按钮点击与自动新增触发冲突
for i in range(len(st.session_state.input_boxes)):
    st.text_area(
        f"内容 {i+1}：",
        height=100,
        key=f"input_box_{i}",
        placeholder="请输入飞书链接或直接粘贴文本...",
    )

col_add, col_extract = st.columns([1, 4])

with col_add:
    if st.button("➕ 新增输入框"):
        st.session_state.input_boxes.append("")
        st.rerun()

with col_extract:
    if st.button("🚀 提取当前框内文案", use_container_width=True):
        all_inputs = []
        for i in range(len(st.session_state.input_boxes)):
            val = st.session_state.get(f"input_box_{i}", "").strip()
            if val:
                all_inputs.append(val)
                
        if not all_inputs:
            st.warning("请至少输入一个有效内容")
        else:
            new_inputs = [v for v in all_inputs if v not in st.session_state.processed_inputs]
            if not new_inputs:
                st.info("没有新增的链接/文本需要提取（之前的已提取过）。")
            else:
                success_parts, _failed_parts = process_extraction(new_inputs)
                if success_parts:
                    st.session_state.processed_inputs.update(success_parts)
                st.rerun()

if st.session_state.extracted_list:
    st.header("2. 审核与编辑文案")
    
    if st.button("🗑️ 清空列表"):
        st.session_state.extracted_list = []
        st.session_state.processed_inputs = set()
        st.session_state.card_generated = False
        st.rerun()
        
    edited_list = []
    categories = ["重点能力", "通用能力", "搜索能力", "推荐能力", "对话能力"]
    
    with st.container():
        # 为所有提取的项目创建 Tabs
        if len(st.session_state.extracted_list) > 0:
            tab_titles = [f"项目 {i+1}" for i in range(len(st.session_state.extracted_list))]
            project_tabs = st.tabs(tab_titles)
            
            # 遍历每个 Tab 渲染内容
            for i, (tab, data) in enumerate(zip(project_tabs, st.session_state.extracted_list)):
                with tab:
                    st.markdown(f"**来源:** {data.get('source', '')}")
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        new_title = st.text_input(f"标题", value=data.get("title", ""), key=f"title_{i}")
                    with col2:
                        current_cat = data.get("category", "通用能力")
                        if current_cat not in categories: current_cat = "通用能力"
                        new_cat = st.selectbox(f"分类", categories, index=categories.index(current_cat), key=f"cat_{i}")
                    
                    new_content = st.text_area(f"内容", value=data.get("content", ""), height=100, key=f"content_{i}")
                    
                    # 增加图片上传组件
                    uploaded_file = st.file_uploader("上传该模块的图片 (支持动图/静图)", type=['png', 'jpg', 'jpeg', 'gif'], key=f"img_upload_{i}")
                    last_uploaded_name_key = f"last_uploaded_name_{i}"
                    
                    if uploaded_file is not None:
                        # 如果是新选择的图片，自动触发上传
                        if st.session_state.get(last_uploaded_name_key) != uploaded_file.name:
                            with st.spinner("检测到新图片，正在自动上传到飞书..."):
                                try:
                                    img_key = upload_image_to_feishu(uploaded_file.getvalue())
                                    st.session_state.extracted_list[i]["img_key"] = img_key
                                    st.session_state[last_uploaded_name_key] = uploaded_file.name
                                    st.success(f"✅ 图片上传成功! img_key: {img_key}")
                                except Exception as e:
                                    st.error(f"❌ 上传失败: {e}")
                    else:
                        # 如果用户清空了图片选择器，也清空已上传的图片记录
                        if st.session_state.get(last_uploaded_name_key):
                            st.session_state[last_uploaded_name_key] = None
                            st.session_state.extracted_list[i]["img_key"] = ""
                    
                    if st.session_state.extracted_list[i].get("img_key"):
                        st.info(f"✅ 已准备好图片: {st.session_state.extracted_list[i].get('img_key')}")
                    
                    # AI 二次润色
                    with st.expander("✨ 让 AI 帮忙修改这段文案"):
                        st.text_input("你想怎么修改？ (例如: '语气更活泼一点' 或 '把某某卖点加上')", key=f"refine_req_input_{i}")
                        
                        # 使用回调函数处理按钮点击，避免渲染顺序导致的覆盖问题
                        def do_refine(index=i):
                            # 直接从 st.session_state 读取最新的用户输入值，而不是传参
                            req = st.session_state.get(f"refine_req_input_{index}", "")
                            current_content = st.session_state.get(f"content_{index}", "")
                            
                            if req.strip():
                                try:
                                    # 调用大模型
                                    new_text = refine_text_with_ai(current_content, req)
                                    
                                    # 1. 记录优化历史，不直接覆盖原始文案
                                    if "refined_history" not in st.session_state.extracted_list[index]:
                                        st.session_state.extracted_list[index]["refined_history"] = []
                                        
                                    # 将最新生成的文案插到最前面
                                    st.session_state.extracted_list[index]["refined_history"].insert(0, {
                                        "req": req,
                                        "text": new_text
                                    })
                                    
                                    # 2. 顺便清空润色要求框，方便下次输入
                                    st.session_state[f"refine_req_input_{index}"] = ""
                                except Exception as e:
                                    st.session_state[f"refine_error_{index}"] = str(e)
                        
                        st.button(f"✨ 生成优化文案", key=f"btn_refine_{i}", on_click=do_refine)
                        
                        if st.session_state.get(f"refine_error_{i}"):
                            st.error(f"优化失败: {st.session_state[f'refine_error_{i}']}")
                            del st.session_state[f"refine_error_{i}"]
        
                        history = st.session_state.extracted_list[i].get("refined_history", [])
                        if history:
                            st.markdown("#### 💡 优化结果历史")
                            
                            # 提示采纳成功的状态
                            if st.session_state.get(f"adopted_{i}"):
                                st.success("✅ 已成功采纳该版本！上方的文案已更新。")
                                st.session_state[f"adopted_{i}"] = False
                                
                            # 使用内部标签页(Tabs)进行历史版本的横向排版
                            history_tab_names = [f"版本 {len(history)-j}" for j in range(len(history))]
                            if history_tab_names:
                                history_tab_names[0] += " (最新)"
                                
                            history_tabs = st.tabs(history_tab_names)
                            for j, (h_tab, item) in enumerate(zip(history_tabs, history)):
                                with h_tab:
                                    st.markdown(f"**修改要求:** {item['req']}")
                                    st.info(item['text'])
                                    
                                    def adopt_text(index=i, text=item['text']):
                                        # 用户手动点击采纳时，才替换主文本框的内容
                                        st.session_state[f"content_{index}"] = text
                                        st.session_state.extracted_list[index]["content"] = text
                                        # 设置采纳成功的标志位
                                        st.session_state[f"adopted_{index}"] = True
                                        
                                    st.button(f"⬆️ 采纳此版本", key=f"adopt_{i}_{j}", on_click=adopt_text)
                    
                    # 这里的 edited_list 是用来在点击"生成卡片"时保存所有最终状态的
                    edited_list.append({
                        "title": new_title,
                        "category": new_cat,
                        "content": new_content,
                        "source": data.get("source", ""),
                        "img_key": st.session_state.extracted_list[i].get("img_key", "")
                    })
            
        st.markdown("---")
        
        col_translate, col_gen = st.columns(2)
        with col_translate:
            if st.button("🌐 确认中文无误，生成英文翻译版"):
                st.session_state.extracted_list = edited_list
                with st.spinner("正在将新增的中文文案翻译为英文..."):
                    try:
                        if "english_list" not in st.session_state:
                            st.session_state.english_list = []
                            
                        new_english_list = []
                        for idx, item in enumerate(edited_list):
                            # 如果旧的英文翻译存在，保留以避免重复翻译
                            if idx < len(st.session_state.english_list):
                                new_english_list.append(st.session_state.english_list[idx])
                            else:
                                # 只有新追加的内容才调用模型翻译
                                eng_title = translate_to_english(item["title"])
                                eng_content = translate_to_english(item["content"])
                                new_english_list.append({
                                    "title": eng_title,
                                    "category": item["category"],
                                    "content": eng_content,
                                    "source": item["source"],
                                    "img_key": ""  # 英文图片独立上传
                                })
                        st.session_state.english_list = new_english_list
                        st.session_state.show_english_review = True
                        st.success("翻译完成，请在下方审核英文文案！")
                    except Exception as e:
                        st.error(f"翻译失败: {e}")
        
        with col_gen:
            if st.button("✅ 仅生成中文飞书卡片"):
                st.session_state.extracted_list = edited_list
                with st.spinner("正在组装生成中文卡片..."):
                    try:
                        template = load_template(_template_path('AI搜索引擎功能更新卡片模版 .card'))
                        card = generate_card_from_template(template, edited_list)
                        output_file = 'generated_card_web.card'
                        save_card(card, output_file)
                        
                        st.session_state.card_generated = True
                        st.session_state.only_chinese = True
                        st.success("🎉 中文卡片生成成功！")
                    except Exception as e:
                        import traceback
                        st.error(f"生成卡片失败: {e}")
                        st.code(traceback.format_exc())

    if st.session_state.get("show_english_review") and "english_list" in st.session_state:
        st.header("3. 审核与编辑英文文案")
        
        english_edited_list = []
        
        with st.container():
            if len(st.session_state.english_list) > 0:
                eng_tab_titles = [f"Project {i+1} (English)" for i in range(len(st.session_state.english_list))]
                eng_tabs = st.tabs(eng_tab_titles)
                
                for i, (tab, data) in enumerate(zip(eng_tabs, st.session_state.english_list)):
                    with tab:
                        st.markdown(f"**Source:** {data.get('source', '')}")
                        new_eng_title = st.text_input(f"Title (English)", value=data.get("title", ""), key=f"eng_title_{i}")
                        new_eng_content = st.text_area(f"Content (English)", value=data.get("content", ""), height=100, key=f"eng_content_{i}")
                        
                        # 增加英文版图片上传组件
                        uploaded_eng_file = st.file_uploader("Upload Image for English Version", type=['png', 'jpg', 'jpeg', 'gif'], key=f"eng_img_upload_{i}")
                        eng_last_uploaded_name_key = f"eng_last_uploaded_name_{i}"
                        
                        if uploaded_eng_file is not None:
                            if st.session_state.get(eng_last_uploaded_name_key) != uploaded_eng_file.name:
                                with st.spinner("Uploading new image to Feishu..."):
                                    try:
                                        img_key = upload_image_to_feishu(uploaded_eng_file.getvalue())
                                        st.session_state.english_list[i]["img_key"] = img_key
                                        st.session_state[eng_last_uploaded_name_key] = uploaded_eng_file.name
                                        st.success(f"✅ Upload success! img_key: {img_key}")
                                    except Exception as e:
                                        st.error(f"❌ Upload failed: {e}")
                        else:
                            if st.session_state.get(eng_last_uploaded_name_key):
                                st.session_state[eng_last_uploaded_name_key] = None
                                st.session_state.english_list[i]["img_key"] = ""
                        
                        if st.session_state.english_list[i].get("img_key"):
                            st.info(f"✅ Uploaded Image Key: {st.session_state.english_list[i].get('img_key')}")
                        
                        english_edited_list.append({
                            "title": new_eng_title,
                            "category": data.get("category"),
                            "content": new_eng_content,
                            "source": data.get("source", ""),
                            "img_key": st.session_state.english_list[i].get("img_key", "")
                        })
                        
        st.markdown("---")
        if st.button("✅ 生成双语飞书卡片 (中文 + 英文)"):
            st.session_state.extracted_list = edited_list
            st.session_state.english_list = english_edited_list
            with st.spinner("正在组装生成双语卡片..."):
                try:
                    # 生成中文
                    zh_template = load_template(_template_path('AI搜索引擎功能更新卡片模版 .card'))
                    zh_card = generate_card_from_template(zh_template, edited_list)
                    zh_output_file = 'generated_card_web.card'
                    save_card(zh_card, zh_output_file)
                    
                    # 生成英文
                    en_template = load_template(_template_path('【英文】AI搜索引擎卡片模版.card'))
                    en_card = generate_card_from_template(en_template, english_edited_list)
                    en_output_file = 'generated_card_web_en.card'
                    save_card(en_card, en_output_file)
                    
                    st.session_state.card_generated = True
                    st.session_state.only_chinese = False
                    st.success("🎉 双语卡片生成成功！")
                except Exception as e:
                    import traceback
                    st.error(f"生成双语卡片失败: {e}")
                    st.code(traceback.format_exc())

    if st.session_state.get("card_generated"):
        st.markdown("### 下载区域")
        col_dl1, col_dl2 = st.columns(2)
        
        with col_dl1:
            zh_output_file = 'generated_card_web.card'
            if os.path.exists(zh_output_file):
                with open(zh_output_file, "r", encoding="utf-8") as f:
                    zh_card_json = f.read()
                    
                st.download_button(
                    label="⬇️ 下载生成的飞书卡片 - 中文版 (.card)",
                    data=zh_card_json,
                    file_name="generated_card_web_zh.card",
                    mime="application/json",
                    use_container_width=True
                )
                
        with col_dl2:
            if not st.session_state.get("only_chinese", True):
                en_output_file = 'generated_card_web_en.card'
                if os.path.exists(en_output_file):
                    with open(en_output_file, "r", encoding="utf-8") as f:
                        en_card_json = f.read()
                        
                    st.download_button(
                        label="⬇️ 下载生成的飞书卡片 - 英文版 (.card)",
                        data=en_card_json,
                        file_name="generated_card_web_en.card",
                        mime="application/json",
                        use_container_width=True
                    )
