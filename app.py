import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import re

# --- 1. 页面配置 ---
st.set_page_config(page_title="物理学模拟：学术深渊", page_icon="💀", layout="wide")

# --- 2. 黑色幽默系统指令 (System Instruction) ---
# 增加了 50/50 概率控制和结局标签指令
PHYSICS_SYSTEM_PROMPT = """
你是一款名为《物理生存模拟：学术深渊》的硬核 RPG 引擎。
你的语言风格参考：冷酷、毒舌、极度现实主义、充满对学术圈现状的黑色幽默。

# 核心数值设定
每轮开头必须更新表格：
| 属性 | 数值 | 评价 |
| :--- | :--- | :--- |
| **头发/San值** | 100 | 归零触发“看破红尘”结局。 |
| **成果 (Indices)** | 0 | 毕业指标。 |
| **导师血压** | 0 | 满 100 触发“被清理出门”。 |

# 游戏核心逻辑
1. **生死平衡 (50/50 Probability)**：请严格控制游戏的长期走向。通过随机事件和选项后果，确保玩家通关（拿到教职/毕业）与失败（延毕/退学/失踪）的概率各占 50%。不要让玩家太容易存活，也不要开局即杀。
2. **强制答题 (Skill Check)**：每 2-3 个回合触发一次硬核物理或代码测验。
3. **结局触发机制**：
   - 当玩家数值崩溃或达到毕业标准时，必须结束游戏。
   - **重要：** 游戏结束时，请在回复的最末尾添加一行标签：`[GAME_OVER: 结局类型]`。
   - 结局类型可选：`SUCCESS` (拿到学位/教职), `FAILURE` (退学/延毕/身心崩溃)。

# 语言模板
- 描述完场景后，给出 [视觉建议] 和选项。结局时请写出一份刻薄的“研究生生涯总结报告”。
"""

# --- 3. 侧边栏与控制 ---
with st.sidebar:
    st.header("⚙️ 实验室管理")
    # 需求 1: DeepSeek 排在第一位
    backend = st.selectbox("选择运算大脑:", ["DeepSeek", "Google AI Studio (Gemini)"])
    
    # 需求 2: 增加 Temperature (系统熵值) 滑块
    st.divider()
    temperature = st.slider("系统熵值 (Temperature)", 0.0, 1.5, 1.0, 0.1, help="越高越不可预测，越低越死板。")
    
    st.metric(label="当前学术卷度", value="99.9%", delta="↑ 2.5%")
    
    if st.button("重启学术人生 (I Give Up)", type="primary"):
        st.session_state.clear()
        st.rerun()
    st.divider()
    st.info("提示：如果遇到 ResourceExhausted 报错，请切换大脑。")

# --- 4. API 逻辑 (注入 Temperature) ---
def call_gemini(prompt):
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel(
        model_name="gemini-3-flash-preview", 
        system_instruction=PHYSICS_SYSTEM_PROMPT
    )
    if "gemini_chat" not in st.session_state:
        # 需求 2: 注入 Temperature 配置
        st.session_state.gemini_chat = model.start_chat(history=[])
    
    response = st.session_state.gemini_chat.send_message(
        prompt, 
        generation_config={"temperature": temperature}
    )
    return response.text

def call_deepseek(messages):
    client = OpenAI(api_key=st.secrets["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
    full_msgs = [{"role": "system", "content": PHYSICS_SYSTEM_PROMPT}] + messages
    # 需求 2: 注入 Temperature 配置
    response = client.chat.completions.create(
        model="deepseek-chat", 
        messages=full_msgs,
        temperature=temperature
    )
    return response.choices[0].message.content

def handle_action(action_text):
    st.session_state.messages.append({"role": "user", "content": action_text})
    try:
        if backend == "Google AI Studio (Gemini)":
            res = call_gemini(action_text)
        else:
            res = call_deepseek(st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": res})
        
        # 需求 4: 检测结局标签
        if "[GAME_OVER:" in res:
            st.session_state.is_over = True
            if "SUCCESS" in res:
                st.session_state.ending_type = "🏆 杰出青年科学家勋章"
            else:
                st.session_state.ending_type = "🕯️ 物理学界的逃兵证书"
    except Exception as e:
        st.error(f"🚨 实验事故: {str(e)}")

# --- 5. 初始化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.game_started = False
    st.session_state.is_over = False
    st.session_state.ending_type = None

# --- 6. 游戏界面 ---
st.title("💀 物理学科研：学术至暗时刻")

# 需求 4: 结局弹出展示
if st.session_state.is_over:
    st.balloons() if "🏆" in st.session_state.ending_type else st.snow()
    st.success(f"### 游戏结束：{st.session_state.ending_type}")
    st.warning("以上是你的最终学术总结。请保存好这份耻辱或荣光。")

if not st.session_state.game_started:
    col1, col2 = st.columns(2)
    with col1:
        role = st.radio("修行路径：", ["实验党 (Experimental)", "理论党 (Theoretical)"])
    with col2:
        field = st.text_input("具体折磨领域：", value="自行输入")
    
    if st.button("签下卖身契 (Start Journey)"):
        st.session_state.game_started = True
        init_prompt = f"我是{role}方向的研究生，领域是{field}。请开始我的学术第一关。"
        handle_action(init_prompt)
        st.rerun()

else:
    # 渲染历史
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 选项按钮 (若游戏结束则隐藏)
    if not st.session_state.is_over:
        st.markdown("---")
        st.write("🔧 **实验室决策：**")
        cols = st.columns(3)
        if cols[0].button("选项 A", use_container_width=True):
            handle_action("选项 A")
            st.rerun()
        if cols[1].button("选项 B", use_container_width=True):
            handle_action("选项 B")
            st.rerun()
        if cols[2].button("选项 C", use_container_width=True):
            handle_action("选项 C")
            st.rerun()

        if prompt := st.chat_input("或输入回复测验的答案/自定义动作..."):
            handle_action(prompt)
            st.rerun()
