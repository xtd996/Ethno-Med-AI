import importlib.util
import json
import os
import time
import uuid

import requests
import streamlit as st

st.set_page_config(
    page_title="智能问答助手",  # 改为更通用的标题
    page_icon="🤖",
    initial_sidebar_state="auto",
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
<style>
body {
    background-color: #f9f9f9;
    color: #333;
    font-family: 'Roboto', sans-serif;
}
div[data-testid="stAppViewContainer"] > .main {
    padding: 0 20px;
    max-width: 1800px;
    margin: 0 auto;
}
.main {
    overflow-y: auto;
    padding: 20px;
    background-color: #ffffff;
    border-radius: 10px;
    margin-bottom: 80px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
    width: 90%;
    max-width: 1800px;
    margin-left: auto;
    margin-right: auto;
}
.chat-input-container {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 15px;
    background: #ffffff;
    box-shadow: 0 -3px 10px rgba(0, 0, 0, 0.1);
    border-top: 1px solid #e0e0e0;
}
.stChatMessage {
    max-width: 85% !important;
    padding: 10px 15px;
    border-radius: 15px;
    margin: 10px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
.stChatMessage.user {
    background-color: #007bff;
    color: white;
    margin-left: auto;
    text-align: right;
}
.stChatMessage.assistant {
    background-color: #e9ecef;
    color: #333;
    margin-right: auto;
}
.stChatMessage .stAvatar {
    width: 32px !important;
    height: 32px !important;
    border-radius: 50%;
    margin-right: 10px;
}
.stSidebar {
    background-color: #f0f4f8;
    padding: 20px;
    border-right: 1px solid #d0d7de;
}
.chat-record-container {
    background-color: #ffffff;
    padding: 10px;
    margin: 5px 0;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    transition: all 0.2s ease;
}
.chat-record-container:hover {
    background-color: #eef2f7;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}
.stButton > button {
    border-radius: 8px;
    background: linear-gradient(90deg, #007bff, #0056b3);
    color: white;
    padding: 10px 15px;
    transition: all 0.3s ease;
}
.stButton > button:hover {
    background: linear-gradient(90deg, #0056b3, #003d80);
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
}
</style>
""", unsafe_allow_html=True)

API_URL = "http://localhost:8000/chat"
SWITCH_MODEL_URL = "http://localhost:8000/switch_model"
headers = {"Content-Type": "application/json"}

# 初始化 session_state
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "current_session_id" not in st.session_state:
    st.session_state["current_session_id"] = None
if "sessions" not in st.session_state:
    st.session_state["sessions"] = {}
if "stop_generation" not in st.session_state:
    st.session_state["stop_generation"] = False
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "主页"
if "selected_model" not in st.session_state:
    st.session_state["selected_model"] = "专业模型"

# 定义 modules 目录路径
modules_directory = "../page"


# 加载和保存历史对话的函数
def load_chat_history():
    history_file = "chat_history.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
                if not history:
                    return []
                if isinstance(history[0], list):
                    return [{"session_id": str(uuid.uuid4()),
                             "first_question": next((msg["content"] for msg in chat if msg["role"] == "user"),
                                                    "新建对话"),
                             "messages": chat} for chat in history]
                return history
        except (json.JSONDecodeError, IOError) as e:
            st.error(f"加载历史对话失败: {str(e)}")
            return []
    return []


def save_chat_history():
    history_file = "chat_history.json"
    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(st.session_state["chat_history"], f, ensure_ascii=False, indent=4)
    except IOError as e:
        st.error(f"保存历史对话失败: {str(e)}")


def save_current_chat():
    if st.session_state["current_session_id"] and st.session_state["sessions"].get(
            st.session_state["current_session_id"]):
        current_messages = st.session_state["sessions"][st.session_state["current_session_id"]]
        current_chat = {
            "session_id": st.session_state["current_session_id"],
            "first_question": next((msg["content"] for msg in current_messages if msg["role"] == "user"), "新建对话"),
            "messages": current_messages.copy()
        }
        existing_session = next((chat for chat in st.session_state["chat_history"] if
                                 chat["session_id"] == st.session_state["current_session_id"]), None)
        if existing_session:
            existing_session.update(current_chat)
        else:
            st.session_state["chat_history"].append(current_chat)
        save_chat_history()


def load_chat(session_id):
    session = next((chat for chat in st.session_state["chat_history"] if chat["session_id"] == session_id), None)
    if session:
        st.session_state["current_session_id"] = session_id
        st.session_state["sessions"][session_id] = session["messages"].copy()
        st.session_state["stop_generation"] = False
        st.rerun()


def create_new_session():
    session_id = str(uuid.uuid4())
    st.session_state["current_session_id"] = session_id
    st.session_state["sessions"][session_id] = []
    return session_id


def switch_model(model_name):
    if model_name != st.session_state["selected_model"]:
        with st.spinner(f"正在切换到 {model_name}，请稍候..."):
            try:
                response = requests.post(SWITCH_MODEL_URL, json={"model_name": model_name}, headers=headers)
                response.raise_for_status()
                if response.json().get("status") == "success":
                    st.session_state["selected_model"] = model_name
                    st.success(f"已切换到 {model_name}")
                    st.rerun()  # 刷新界面以更新标题和消息
                else:
                    st.error("模型切换失败，请重试")
            except requests.RequestException as e:
                st.error(f"模型切换失败: {str(e)}")


def load_page(page_name):
    page_file = os.path.join(modules_directory, f"{page_name}.py")
    if os.path.exists(page_file):
        spec = importlib.util.spec_from_file_location(page_name, page_file)
        page_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(page_module)
        return page_module
    else:
        st.error(f"页面 '{page_name}' 未找到")
        return None


# 在程序启动时加载历史记录并初始化 sessions
if not st.session_state["chat_history"]:
    st.session_state["chat_history"] = load_chat_history()
    for chat in st.session_state["chat_history"]:
        st.session_state["sessions"][chat["session_id"]] = chat["messages"].copy()

if not st.session_state["current_session_id"]:
    create_new_session()

# 侧边栏
with st.sidebar:
    st.header("任务选择")
    page_selection = st.selectbox("选择子页面", ["主页", "文档问答", "联网问答", "新建知识库"])

    if page_selection != st.session_state["current_page"]:
        save_current_chat()
        with st.spinner("页面加载中，请稍候..."):
            st.info("温馨提示：正在切换页面，请稍作等待！")
            time.sleep(0.5)
            st.session_state["current_page"] = page_selection
            st.rerun()

    st.header("模型选择")
    model_options = {
        "生活模型": "未经微调的原模型，用于日常问题",
        "专业模型": "经微调的模型，用于医疗问题"
    }
    selected_model = st.selectbox("选择模型", list(model_options.keys()),
                                  index=list(model_options.keys()).index(st.session_state["selected_model"]))
    if selected_model != st.session_state["selected_model"]:
        switch_model(selected_model)
    st.write(f"模型描述: {model_options[selected_model]}")

    st.header("历史对话")
    if st.button("新建对话"):
        save_current_chat()
        create_new_session()
        st.rerun()

    chat_history = st.session_state["chat_history"]
    if chat_history:
        for i, chat in enumerate(chat_history):
            with st.container():
                col1, col2 = st.columns([7, 1])
                with col1:
                    first_question = chat["first_question"][:20] + "..." if len(chat["first_question"]) > 20 else chat[
                        "first_question"]
                    if st.button(f"对话 {i + 1}: {first_question}", key=f"chat_load_{i}"):
                        load_chat(chat["session_id"])
                with col2:
                    if st.button("⋮", key=f"options_{i}"):
                        st.session_state[f"show_options_{i}"] = not st.session_state.get(f"show_options_{i}", False)
                if st.session_state.get(f"show_options_{i}", False):
                    with st.expander("操作选项"):
                        if st.button(f"删除对话 {i + 1}", key=f"delete_{i}"):
                            st.session_state["chat_history"].pop(i)
                            if chat["session_id"] in st.session_state["sessions"]:
                                del st.session_state["sessions"][chat["session_id"]]
                            if st.session_state["current_session_id"] == chat["session_id"]:
                                create_new_session()
                            save_chat_history()
                            st.rerun()

# 主页面逻辑
if page_selection == "主页":
    # 根据当前模型动态调整标题和描述
    if st.session_state["selected_model"] == "专业模型":
        st.markdown('<h1 style="color: #007bff;">🏥 医疗问答助手</h1>', unsafe_allow_html=True)
        st.markdown('<p style="font-size: 16px; color: #666;">💊 您的专业医疗助手，随时为您解答</p>',
                    unsafe_allow_html=True)
    else:  # 生活模型
        st.markdown('<h1 style="color: #28a745;">🌟 生活小助手</h1>', unsafe_allow_html=True)
        st.markdown('<p style="font-size: 16px; color: #666;">😊 您的日常伙伴，陪您聊聊生活琐事</p>',
                    unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="main">', unsafe_allow_html=True)
        current_messages = st.session_state["sessions"].get(st.session_state["current_session_id"], [])
        if not current_messages:
            if st.session_state["selected_model"] == "专业模型":
                st.chat_message("assistant", avatar="👨‍⚕️").markdown(
                    "您好！我是您的医疗问答助手，请问有什么可以帮助您的？")
            else:  # 生活模型
                st.chat_message("assistant", avatar="🤖").markdown("嗨！我是您的生活小助手，有什么想聊的吗？")
        else:
            for msg in current_messages:
                avatar = "👨‍⚕️" if msg["role"] == "assistant" and st.session_state[
                    "selected_model"] == "专业模型" else "🤖" if msg["role"] == "assistant" else "👨"
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"])
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)
    prompt = st.chat_input("请输入您的问题或查询...")
    st.markdown('</div>', unsafe_allow_html=True)

    if prompt:
        current_messages = st.session_state["sessions"][st.session_state["current_session_id"]]
        current_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👨"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="👨‍⚕️" if st.session_state["selected_model"] == "专业模型" else "🤖"):
            msg_placeholder = st.empty()
            reply_text = ""
            stop_container = st.empty()
            stop_button = stop_container.button("停止生成", key=f"stop_gen_{time.time()}")

            data = {"messages": current_messages}
            try:
                with st.spinner("💡 正在为您生成回答，请稍候..." if st.session_state[
                                                                      "selected_model"] == "专业模型" else "🌈 正在思考您的提问..."):
                    with requests.post(API_URL, json=data, headers=headers, stream=True) as response:
                        response.raise_for_status()
                        for chunk in response.iter_content(chunk_size=64):
                            if chunk and not st.session_state["stop_generation"]:
                                chunk_text = chunk.decode("utf-8", errors="ignore")
                                reply_text += chunk_text
                                msg_placeholder.markdown(reply_text + "▌")
                            if stop_button or st.session_state["stop_generation"]:
                                st.session_state["stop_generation"] = True
                                break
                msg_placeholder.markdown(reply_text)
            except requests.RequestException as e:
                reply_text = f"❌ 发生错误：{str(e)}"
                msg_placeholder.markdown(reply_text)

            stop_container.empty()
            if st.session_state["stop_generation"]:
                reply_text = reply_text if reply_text else "生成已手动停止。"
            st.session_state["stop_generation"] = False
            current_messages.append({"role": "assistant", "content": reply_text})

# 子页面逻辑
elif page_selection == "文档问答":
    save_current_chat()
    page_module = load_page("文档问答")
    if page_module:
        try:
            page_module.run()
        except AttributeError:
            st.error("子页面缺少 'run' 函数或未正确定义")

elif page_selection == "联网问答":
    save_current_chat()
    page_module = load_page("联网问答")
    if page_module:
        try:
            page_module.run()
        except AttributeError:
            st.error("子页面缺少 'run' 函数或未正确定义")


