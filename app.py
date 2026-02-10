import streamlit as st
import google.generativeai as genai
from openai import OpenAI

# --- 1. 页面配置 ---
st.set_page_config(page_title="物理学模拟器", page_icon="⚛️", layout="wide")

# 通用学术深渊指令
PHYSICS_SYSTEM_PROMPT = """
你是一款名为《物理生存模拟：学术深渊》的硬核文字 RPG 引擎。
# 核心数值追踪
每轮回复开头必须更新 Markdown 表格：| 属性 | 数值 | 说明 |
# 游戏逻辑设定
1. 分支：实验物理 (Experimental) 或 理论/计算物理 (Theoretical/Comp)。
2. 通用梗：Reviewer 2 的刁难、arXiv 抢发、报账系统崩溃、由于液氮断供导致的实验失败。
3. 选项：提供 A/B/C 三个带概率随机后果的选项。
"""

# --- 2. 侧边栏：引擎切换 ---
with st.sidebar:
    st.header("⚙️ 引擎控制")
    backend = st.selectbox(
        "选择运算大脑 (API Provider):",
        ["Google AI Studio (Gemini)", "DeepSeek"]
    )
    if st.button("重启学术生涯", type="primary"):
        st.session_state.clear()
        st.rerun()
    st.info("提示：如果 Gemini 报错‘资源耗尽’，请切换到 DeepSeek。")

# --- 3. API 调用函数 ---
def call_gemini(prompt):
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel(
        model_name="gemini-3-flash-preview", # 建议使用正式版名称
        system_instruction=PHYSICS_SYSTEM_PROMPT
    )
    if "gemini_chat" not in st.session_state:
        st.session_state.gemini_chat = model.start_chat(history=[])
    response = st.session_state.gemini_chat.send_message(prompt)
    return response.text

def call_deepseek(messages):
    client = OpenAI(api_key=st.secrets["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
    full_msgs = [{"role": "system", "content": PHYSICS_SYSTEM_PROMPT}] + messages
    response = client.chat.completions.create(model="deepseek-chat", messages=full_msgs)
    return response.choices[0].message.content

# --- 4. 核心逻辑处理函数 ---
def handle_action(action_text):
    """处理玩家输入（无论是按钮点击还是手动输入）"""
    st.session_state.messages.append({"role": "user", "content": action_text})
    try:
        if backend == "Google AI Studio (Gemini)":
            res = call_gemini(action_text)
        else:
            res = call_deepseek(st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": res})
    except Exception as e:
        st.error(f"🚨 引擎报错：{str(e)}")

# --- 5. 状态初始化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.game_started = False

# --- 6. UI 界面 ---
st.title("🧬 物理学科研生存模拟器")

if not st.session_state.game_started:
    col1, col2 = st.columns(2)
    with col1:
        role = st.radio("修行路径：", ["实验物理 (Experimental)", "理论物理 (Theoretical)"])
    with col2:
        field = st.text_input("研究领域：", value="凝聚态 / 量子信息 / 统计力学")
    
    if st.button("进入学术炼狱 (Start Journey)"):
        st.session_state.game_started = True
        init_prompt = f"我是{role}方向的研究生，领域是{field}。请开始我的第一关：开题报告。"
        handle_action(init_prompt)
        st.rerun()

else:
    # 渲染历史对话
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    st.divider()
    
    # --- 可视化按钮组 ---
    st.write("请做出你的抉择：")
    btn_cols = st.columns(3)
    
    if btn_cols[0].button("选项 A", use_container_width=True):
        handle_action("A")
        st.rerun()
    if btn_cols[1].button("选项 B", use_container_width=True):
        handle_action("B")
        st.rerun()
    if btn_cols[2].button("选项 C", use_container_width=True):
        handle_action("C")
        st.rerun()

    # 保留手动输入框，用于输入自定义动作（如：我决定去摸鱼）
    if prompt := st.chat_input("或在这里输入自定义动作..."):
        handle_action(prompt)
        st.rerun()
