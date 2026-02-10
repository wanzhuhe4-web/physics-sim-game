import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import re

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="物理学生存模拟：从入门到入土",
    page_icon="⚗️",
    layout="wide"
)

# --- 2. 系统指令 ---
PHYSICS_SYSTEM_PROMPT = """
你是一款名为《物理学生存模拟》的文字 RPG 引擎。
语言风格幽默风趣，充满讽刺意味。

# 核心数值 (每轮更新)
| 属性 | 当前值 | 物理学定义 |
| :--- | :--- | :--- |
| **头皮反光度** | 0% | 0%为黑体，100%为全反射镜面（绝世强者）。 |
| **精神熵** | Low | 达到“热寂”(Max) 则疯掉退学。 |
| **导师杀意**| 0% | 达到 100% 触发“逐出师门”。 |
| **学术垃圾**| 0篇 | 毕业硬通货。 |

# 游戏循环机制
游戏以 **4 个回合**为一个周期：
1. **第 1-3 回合**：剧情推进，必须给出 A/B/C
2. **第 4 回合**：
   - 触发 `[EVENT: QUIZ]`
   - 不给剧情选项
3. **考核结算**：
   - 收到 `[ANSWER_QUIZ]`
   - 评分后立刻回到剧情
"""

# --- 3. 初始化状态 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.game_started = False
    st.session_state.is_over = False
    st.session_state.ending_type = None
    st.session_state.final_report = ""
    st.session_state.round_count = 0
    st.session_state.mode = "NORMAL"
    st.session_state.event_content = ""
    st.session_state.field = ""

# --- 4. API ---
def get_ai_response(prompt, backend, temperature):
    try:
        if backend == "Google AI Studio (Gemini)":
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel(
                model_name="gemini-3-flash-preview",
                system_instruction=PHYSICS_SYSTEM_PROMPT
            )
            if "gemini_chat" not in st.session_state:
                st.session_state.gemini_chat = model.start_chat(history=[])
            return st.session_state.gemini_chat.send_message(
                prompt,
                generation_config={"temperature": temperature}
            ).text
        else:
            client = OpenAI(
                api_key=st.secrets["DEEPSEEK_API_KEY"],
                base_url="https://api.deepseek.com"
            )
            msgs = [{"role": "system", "content": PHYSICS_SYSTEM_PROMPT}]
            msgs += st.session_state.messages
            msgs.append({"role": "user", "content": prompt})
            return client.chat.completions.create(
                model="deepseek-chat",
                messages=msgs,
                temperature=temperature
            ).choices[0].message.content
    except Exception as e:
        return f"🚨 API Error: {str(e)}"

# --- 5. 核心动作 ---
def handle_action(action_text, input_type="ACTION", display_text=None):
    prefix = {
        "ACTION": "【作死】",
        "QUIZ_ANSWER": "【答辩】",
        "REBUTTAL": "【卑微回复】"
    }

    user_content = display_text if display_text else f"{prefix.get(input_type,'')} {action_text}"
    st.session_state.messages.append({"role": "user", "content": user_content})

    if input_type == "ACTION":
        st.session_state.round_count += 1

    force_quiz = (
        input_type == "ACTION"
        and not st.session_state.is_over
        and st.session_state.round_count > 0
        and st.session_state.round_count % 4 == 0
    )

    # Prompt 构建
    if input_type == "QUIZ_ANSWER":
        prompt = f"[ANSWER_QUIZ]: {action_text}。请评分，然后继续主线剧情，必须给出 A/B/C 三个选项。"
        st.session_state.mode = "NORMAL"

    elif input_type == "REBUTTAL":
        prompt = f"[GRADE: REBUTTAL]: {action_text}。继续剧情，给出 A/B/C。"
        st.session_state.mode = "NORMAL"

    else:
        if force_quiz:
            field = st.session_state.field or "物理"
            prompt = (
                f"{action_text}（系统指令：第 {st.session_state.round_count} 轮，"
                f"强制考核回合。不要给剧情选项，直接触发 [EVENT: QUIZ]，"
                f"围绕 {field} 出一道单项选择题，给 A/B/C。）"
            )
        else:
            prompt = f"{action_text}（请给出 A/B/C 三个选项）"

    backend = st.session_state.get("backend_selection", "Google AI Studio (Gemini)")
    temperature = st.session_state.get("temperature_setting", 1.0)

    with st.spinner("🧠 导师正在沉思..."):
        res = get_ai_response(prompt, backend, temperature)

    new_mode = "NORMAL"
    clean_res = res

    if "[GAME_OVER:" in res:
        st.session_state.is_over = True
        st.session_state.final_report = re.sub(r"\[GAME_OVER:.*\]", "", res).strip()
        clean_res = st.session_state.final_report

    elif "[EVENT: QUIZ]" in res:
        new_mode = "QUIZ"
        parts = res.split("[EVENT: QUIZ]")
        clean_res = parts[0].strip()
        st.session_state.event_content = parts[1].strip()
        st.toast("⚠️ 考核回合！", icon="🚨")

    if clean_res:
        st.session_state.messages.append({"role": "assistant", "content": clean_res})

    st.session_state.mode = new_mode

# --- 6. 主界面 ---
st.title("⚗️ 物理学生存模拟：从入门到入土")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

st.divider()

# =========================
# 核心交互区（关键修改）
# =========================

# --- QUIZ：显示 A/B/C 按钮 ---
if st.session_state.mode == "QUIZ":
    st.warning("🚨 **考核时刻：导师的死亡凝视**")
    st.markdown(st.session_state.event_content)

    cols = st.columns(3)
    if cols[0].button("A", use_container_width=True):
        handle_action("A", "QUIZ_ANSWER")
        st.rerun()
    if cols[1].button("B", use_container_width=True):
        handle_action("B", "QUIZ_ANSWER")
        st.rerun()
    if cols[2].button("C", use_container_width=True):
        handle_action("C", "QUIZ_ANSWER")
        st.rerun()

# --- NORMAL：原样保留 ---
else:
    st.write("🔧 **抉择时刻：**")
    cols = st.columns(3)
    if cols[0].button("A", use_container_width=True):
        handle_action("A", "ACTION")
        st.rerun()
    if cols[1].button("B", use_container_width=True):
        handle_action("B", "ACTION")
        st.rerun()
    if cols[2].button("C", use_container_width=True):
        handle_action("C", "ACTION")
        st.rerun()

    if prompt := st.chat_input("自定义作死操作..."):
        handle_action(prompt, "ACTION")
        st.rerun()
