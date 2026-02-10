import streamlit as st
import google.generativeai as genai

# --- 1. 基础配置与安全 ---
st.set_page_config(page_title="物理科研模拟器", page_icon="⚛️", layout="wide")

# 从 Streamlit Secrets 获取 API Key
if "GEMINI_API_KEY" not in st.secrets:
    st.error("请在 Streamlit Cloud 的 Secrets 中设置 GEMINI_API_KEY。")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- 2. 物理学硬核系统指令 (System Instruction) ---
# 这里融合了用户的真实科研背景：Octopus 软件、ada 集群、强场物理等
PHYSICS_SYSTEM_PROMPT = """
你是一款名为《物理生存模拟：从 HUST 到诺奖》的硬核 RPG 游戏引擎。
玩家群体：物理系博士生、青年教师。

# 核心数值追踪
每轮必须在开头显示以下 Markdown 表格：
| 头发/San值 | 成果(PRL/Nature) | 机时/经费 | 导师好感度 |
| :--- | :--- | :--- | :--- |

# 游戏逻辑与背景设定
1. 分支选择：实验物理（聚焦激光、真空、光路调校）或理论物理（聚焦公式、计算物理、Octopus软件、SLURM脚本）。
2. 硬核挑战：
   - 如果是理论/计算分支：加入关于 Octopus 软件 K-point 收敛性、ada 集群 SLURM 脚本报错、或是 TDDFT 计算失败的梗。
   - 如果是实验分支：加入关于强场谷电子学（Valleytronics）、超快激光脉冲失稳、或是实验室液氮泄露的场景。
   - 地点联动：偶尔提及在意大利巴勒莫（Palermo）交流期间的异国科研挑战。
3. 技能测验：随机要求玩家解决一个物理问题，如：普朗克长度量纲分析 $\ell_P = \sqrt{\frac{G\hbar}{c^3}}$，或纠正一段 Python/C++ 代码。

# 语言风格
- 充满冷幽默和黑色幽默。
- 导师语录要扎心（如：“你这个数据，审稿人看了会流泪”）。
- 结局多样化：包括“诺奖得主”、“转行量化大佬”、“资深延毕生”、“烧烤店老板”。
"""

# --- 3. 初始化 AI 引擎 ---
@st.cache_resource
def load_model():
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash", # 使用 Flash 保证响应速度
        system_instruction=PHYSICS_SYSTEM_PROMPT
    )

model = load_model()

# --- 4. Streamlit 会话状态管理 ---
if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(history=[])
    st.session_state.game_started = False
    st.session_state.messages = []

# --- 5. UI 界面展示 ---
st.title("🧬 物理学科研生存模拟器 (v1.0)")
st.markdown("---")

# 侧边栏：显示游戏说明和属性图
with st.sidebar:
    st.header("🎮 游戏控制")
    if st.button("重启学术生涯", type="primary"):
        st.session_state.clear()
        st.rerun()
    
    st.divider()
    st.info("""
    **玩法说明：**
    1. 输入 A/B/C 选择你的行动。
    2. 你也可以直接输入自定义指令，如“我决定去巴勒莫海边思考人生”。
    3. 所有的剧情由 AI 根据物理学知识即兴生成。
    """)

# 初始界面：选择角色
if not st.session_state.game_started:
    col1, col2 = st.columns(2)
    with col1:
        role = st.radio("选择你的物理学家分支：", ["实验物理 (Experimentalist)", "理论/计算物理 (Theorist)"])
    with col2:
        direction = st.text_input("具体研究方向：", value="强场谷电子学 (Strong-field Valleytronics)")
    
    if st.button("开始漫长而痛苦的科研之旅"):
        st.session_state.game_started = True
        intro_prompt = f"我是{role}方向的博士生，研究领域是{direction}。请给我一个充满学术压力的开场场景。"
        
        with st.spinner("AI 正在构思你的导师..."):
            response = st.session_state.chat.send_message(intro_prompt)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.rerun()

# 游戏互动界面
else:
    # 渲染历史对话
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 获取用户输入
    if prompt := st.chat_input("输入你的选择..."):
        # 显示用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # 获取 AI 响应
        with st.chat_message("assistant"):
            with st.spinner("导师正在打字..."):
                response = st.session_state.chat.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})