import streamlit as st
import google.generativeai as genai
from openai import OpenAI

# --- 1. 页面配置 ---
st.set_page_config(page_title="物理学模拟：受难曲", page_icon="💀", layout="wide")

# --- 2. 黑色幽默系统指令 (System Instruction) ---
# 强化了对物理学界痛点的讽刺，并加入了“学术审查/技能测验”的强制要求
PHYSICS_SYSTEM_PROMPT = """
你是一款名为《物理生存模拟：学术深渊》的硬核 RPG 引擎。
你的语言风格参考：冷酷、毒舌、极度现实主义、充满对学术圈现状的黑色幽默。

# 核心数值设定
每轮开头必须更新表格：
| 属性 | 数值 | 评价 |
| :--- | :--- | :--- |
| **头发/San值** | 100 | 归零触发“看破红尘/转行卖红薯”结局。 |
| **成果 (Indices)** | 0 | 毕业指标。别想了，Reviewer 2 正在盯着你。 |
| **导师血压** | 0 | 满 100 触发“逐出师门”。 |

# 游戏核心逻辑
1. 黑色幽默场景：描述要扎心。例如：你在集群上跑了三天的任务因为一个缩进错误挂了；由于实验室由于震动导致激光失稳，而震动源是隔壁装修。
2. **强制答题环节 (Skill Check)**：每 2-3 个回合，必须触发一次“学术审查”或“突发测验”。
   - 题目必须是物理常识或逻辑题。例如：估算黑洞的霍金辐射量级（由于没有公式，让你蒙一个选项）；或者纠正一段 matlab 代码。
   - 答错后果：扣除大量头发，并伴随导师的羞辱。
3. 选项设定：A/B/C 三个选项中。

# 语言模板
- 描述完场景后，给出 [视觉建议] 和选项。
"""

# --- 3. 侧边栏与控制 ---
with st.sidebar:
    st.header("⚙️ 实验室管理")
    backend = st.selectbox("选择运算大脑:", ["Google AI Studio (Gemini)", "DeepSeek"])
    
    # 增加属性展示组件，增加代入感
    st.metric(label="当前学术卷度", value="99.9%", delta="↑ 2.5%")
    
    if st.button("重启学术人生 (I Give Up)", type="primary"):
        st.session_state.clear()
        st.rerun()
    st.divider()
    st.info("提示：如果 Gemini 报错，请切换到 DeepSeek。")

# --- 4. API 逻辑 (保持不变但确保 model_name 正确) ---
def call_gemini(prompt):
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel(
        model_name="gemini-3-flash-preview", # 使用 2026 最新版模型
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

def handle_action(action_text):
    st.session_state.messages.append({"role": "user", "content": action_text})
    try:
        if backend == "Google AI Studio (Gemini)":
            res = call_gemini(action_text)
        else:
            res = call_deepseek(st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": res})
    except Exception as e:
        st.error(f"🚨 实验事故 (API Error): {str(e)}")

# --- 5. 初始化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.game_started = False

# --- 6. 游戏界面 ---
st.title("💀 物理学科研：学术至暗时刻")
st.markdown("> “在物理的世界里，只有真空中的球形奶牛是快乐的。”")

if not st.session_state.game_started:
    col1, col2 = st.columns(2)
    with col1:
        role = st.radio("修行路径：", ["实验党 (Experimental)", "理论党 (Theoretical)"])
    with col2:
        field = st.text_input("具体折磨领域：", value="强场物理 / 凝聚态 / 计算物理 / 超快光学")
    
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

    # 选项按钮
    st.markdown("---")
    st.write("🔧 **实验室决策：**")
    cols = st.columns(3)
    if cols[0].button("A", use_container_width=True):
        handle_action("选项 A")
        st.rerun()
    if cols[1].button("B", use_container_width=True):
        handle_action("选项 B")
        st.rerun()
    if cols[2].button("C", use_container_width=True):
        handle_action("选项 C")
        st.rerun()

    if prompt := st.chat_input("或输入回复测验的答案/自定义动作..."):
        handle_action(prompt)
        st.rerun()



