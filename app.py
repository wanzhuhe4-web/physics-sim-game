import streamlit as st
import google.generativeai as genai

# --- 1. 基础配置 ---
st.set_page_config(page_title="物理学模拟器", page_icon="⚛️", layout="wide")

# 安全读取 API Key
if "GEMINI_API_KEY" not in st.secrets:
    st.error("请在 Streamlit Cloud 的 Secrets 中设置 GEMINI_API_KEY。")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- 2. 通用化系统指令 (System Instruction) ---
# 核心逻辑：提炼全球物理学博士共同的“受难”点
PHYSICS_SYSTEM_PROMPT = """
你是一款名为《物理生存模拟：学术深渊》的硬核文字 RPG 引擎。
你的目标是模拟物理学研究的真实状态，通过黑色幽默让玩家产生共鸣。

# 核心数值追踪
每轮回复开头必须更新 Markdown 表格：
| 属性 | 数值 | 说明 |
| :--- | :--- | :--- |
| **头发/San值** | 100 | 归零触发“看破红尘/转行卖红薯”结局。 |
| **成果 (Indices)** | 0 | 毕业/晋升硬指标，通过发表论文提升。 |
| **经费/资源** | 50 | 实验室的燃料，归零则项目停滞。 |
| **导师/PI 好感度** | 50 | 影响资源分配和推荐信，过低会触发约谈。 |

# 游戏逻辑设定
1. 分支选择：
   - 实验物理 (Experimental)：涉及光路、真空、超导、样本污染、液氦断供。
   - 理论/计算物理 (Theoretical/Comp)：涉及算法发散、超算排队、手推公式发现第一行符号错。
2. 通用学术梗：
   - 审稿人：那个永远无法被取悦的 Reviewer 2。
   - arXiv：上传前一分钟发现同行抢发了类似的成果。
   - 报账：面对毫无逻辑的财务报销流程感到智商归零。
   - 会议：在 Poster 展示区尴尬地对视路人。
3. 技能测验：随机要求玩家回答基础物理概念或纠正一段伪代码。

# 语言风格
- 极具讽刺意味的冷幽默。
- 弱化任何具体的大学名称或具体地理位置。
- 提供三个选项 A/B/C，后果具有概率性的随机波动。
"""

# --- 3. 模型加载 ---
@st.cache_resource
def load_model():
    return genai.GenerativeModel(
        model_name="gemini-3-flash", # 保持最新模型
        system_instruction=PHYSICS_SYSTEM_PROMPT
    )

model = load_model()

# --- 4. 状态管理 ---
if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(history=[])
    st.session_state.game_started = False
    st.session_state.messages = []

# --- 5. UI 界面 ---
st.title("🧬 物理学科研生存模拟器 (Universal Edition)")
st.markdown("---")

with st.sidebar:
    st.header("🎮 控制中心")
    if st.button("重开学术人生", type="primary"):
        st.session_state.clear()
        st.rerun()
    st.divider()
    st.info("**Tips:** 这里没有正确的路，只有头发较少的路。")

# 角色选择
if not st.session_state.game_started:
    col1, col2 = st.columns(2)
    with col1:
        role = st.radio("选择你的科研路径：", ["实验物理 (Experimental)", "理论/计算物理 (Theorist)"])
    with col2:
        direction = st.text_input("研究领域：", value="凝聚态 / 量子信息 / 统计力学")
    
    if st.button("进入学术炼狱 (Enter Purgatory)"):
        st.session_state.game_started = True
        intro_prompt = f"我是{role}方向的研究生，研究领域是{direction}。请开启我的第一关：开题报告。"
        
        with st.spinner("导师正在审批你的开题..."):
            response = st.session_state.chat.send_message(intro_prompt)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.rerun()

# 核心对话
else:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("输入你的抉择 (A/B/C)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("导师正在打字..."):
                response = st.session_state.chat.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})

                st.session_state.messages.append({"role": "assistant", "content": response.text})


