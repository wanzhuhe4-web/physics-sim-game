import streamlit as st
import google.generativeai as genai
from openai import OpenAI

# --- 1. 页面配置 ---
st.set_page_config(page_title="物理学模拟器", page_icon="⚛️", layout="wide")

# 通用学术深渊指令
PHYSICS_SYSTEM_PROMPT = """
你是一款名为《物理生存模拟：学术深渊》的硬核文字 RPG 引擎。
目标受众：全球物理学硕士、博士、青年教师。

# 核心数值追踪
每轮回复开头必须更新 Markdown 表格：
| 属性 | 数值 | 说明 |
| :--- | :--- | :--- |
| **头发/San值** | 100 | 归零触发“退学/转行”结局。 |
| **成果 (Indices)** | 0 | 发表论文提升。毕业/晋升指标。 |
| **资源/经费** | 50 | 实验室的燃料。 |
| **导师好感度** | 50 | 影响资源分配和推荐信。 |

# 游戏逻辑设定
1. 分支：实验物理 (Experimental) 或 理论/计算物理 (Theoretical/Comp)。
2. 通用梗：Reviewer 2 的刁难、arXiv 抢发、报账系统崩溃、由于液氮断供导致的实验失败。
3. 技能测验：随机要求玩家回答物理概念或纠正伪代码。
4. 场景描述：弱化具体大学和地点，聚焦实验室、办公室、学术会议等。
5. 选项：提供 A/B/C 三个带概率随机后果的选项。
"""

# --- 2. 侧边栏：引擎切换 ---
with st.sidebar:
    st.header("⚙️ 引擎控制")
    # 让用户自由切换 API 来源
    backend = st.selectbox(
        "选择运算大脑 (API Provider):",
        ["Google AI Studio (Gemini)", "DeepSeek"]
    )
    
    st.divider()
    if st.button("重启学术生涯", type="primary"):
        st.session_state.clear()
        st.rerun()
    st.info("提示：如果 Gemini 报错‘资源耗尽’，请切换到 DeepSeek。")

# --- 3. API 调用逻辑封装 ---
def call_gemini(prompt):
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel(
        model_name="gemini-3-flash-preview", # 使用正式版名称避免 NotFound
        system_instruction=PHYSICS_SYSTEM_PROMPT
    )
    if "gemini_chat" not in st.session_state:
        st.session_state.gemini_chat = model.start_chat(history=[])
    
    response = st.session_state.gemini_chat.send_message(prompt)
    return response.text

def call_deepseek(messages):
    client = OpenAI(
        api_key=st.secrets["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com"
    )
    # 模拟 System Instruction 效果
    full_msgs = [{"role": "system", "content": PHYSICS_SYSTEM_PROMPT}] + messages
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=full_msgs
    )
    return response.choices[0].message.content

# --- 4. 状态初始化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.game_started = False

# --- 5. 游戏界面 ---
st.title(f"🧬 物理学科研生存模拟器")
st.caption(f"当前驱动引擎：{backend}")

if not st.session_state.game_started:
    col1, col2 = st.columns(2)
    with col1:
        role = st.radio("修行路径：", ["实验物理 (Experimental)", "理论物理 (Theoretical)"])
    with col2:
        field = st.text_input("研究领域：", value="凝聚态 / 量子信息 / 高能物理")
    
    if st.button("进入学术炼狱 (Start Journey)"):
        st.session_state.game_started = True
        init_prompt = f"我是{role}方向的研究生，领域是{field}。请开始我的第一关：开题报告。"
        st.session_state.messages.append({"role": "user", "content": init_prompt})
        
        with st.spinner("导师正在打字..."):
            if backend == "Google AI Studio (Gemini)":
                res = call_gemini(init_prompt)
            else:
                res = call_deepseek([{"role": "user", "content": init_prompt}])
            st.session_state.messages.append({"role": "assistant", "content": res})
        st.rerun()

else:
    # 渲染历史对话
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 玩家输入
    if prompt := st.chat_input("输入你的抉择 A/B/C 或自定义动作..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            try:
                with st.spinner("AI 正在推演命运..."):
                    if backend == "Google AI Studio (Gemini)":
                        res = call_gemini(prompt)
                    else:
                        res = call_deepseek(st.session_state.messages)
                    st.markdown(res)
                    st.session_state.messages.append({"role": "assistant", "content": res})
            except Exception as e:
                # 捕获配额超限等异常并给予友好提示
                st.error("🚨 报错了！可能是当前引擎配额耗尽。")
                st.info("建议在左侧边栏切换到另一个 API 引擎继续游戏。")
                st.write(f"调试信息：{str(e)}")
