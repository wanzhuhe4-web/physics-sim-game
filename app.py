import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import re

# --- 1. 页面配置 (已修改标题) ---
st.set_page_config(
    page_title="物理学生存模拟：从入门到入土", 
    page_icon="⚗️", 
    layout="wide"
)

# --- 2. 核心系统指令 ---
PHYSICS_SYSTEM_PROMPT = """
你是一款名为《物理生存模拟：熵增地狱》的文字 RPG 引擎。
你的身份是**“学术界的墨菲定律化身”**。

# 核心数值 (每轮更新)
| 属性 | 当前值 | 物理学定义 |
| :--- | :--- | :--- |
| **头皮反光度** | 0% | 0%为黑体，100%为全反射镜面（绝世强者）。 |
| **精神熵** | Low | 达到“热寂”(Max) 则疯掉退学。 |
| **导师杀意**| 0% | 达到 100% 触发“逐出师门”。 |
| **学术垃圾**| 0篇 | 毕业硬通货。 |

# 游戏循环机制 (严格执行)
游戏以 **4 个回合**为一个周期：
1. **第 1-3 回合 (剧情)**：正常推进，每次回复末尾必须给出 **A/B/C** 三个选项。
2. **第 4 回合 (考核)**：
   - 当收到指令要求触发考核时，描述完上一轮的后果后，**不要给选项**。
   - 直接触发指令 `[EVENT: QUIZ]`。
   - 出一道极其刁钻的物理简答题。
3. **考核结算**：
   - 收到 `[ANSWER_QUIZ]` 后，进行评分（毒舌点评）。
   - 然后**立即恢复**到剧情模式，给出新一轮的 A/B/C 选项。

# 特殊模式
- **BOSS 战**：收到 `[EVENT: BOSS_BATTLE]` 时进入审稿人对战。
- **结局**：收到 `[GAME_OVER: ...]` 时结束。

# 任务
描述场景 -> 更新数值 -> (根据当前轮次决定是给选项还是出题)。
"""

# --- 3. 初始化状态 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.game_started = False
    st.session_state.is_over = False
    st.session_state.ending_type = None
    st.session_state.final_report = ""
    st.session_state.round_count = 0
    st.session_state.achievements = []
    st.session_state.mode = "NORMAL" # NORMAL, QUIZ, BOSS
    st.session_state.event_content = ""

# --- 4. API 逻辑 ---
def get_ai_response(prompt, backend, temperature):
    try:
        if backend == "Google AI Studio (Gemini)":
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel(model_name="gemini-3-flash-preview", system_instruction=PHYSICS_SYSTEM_PROMPT)
            if "gemini_chat" not in st.session_state: st.session_state.gemini_chat = model.start_chat(history=[])
            return st.session_state.gemini_chat.send_message(prompt, generation_config={"temperature": temperature}).text
        else:
            client = OpenAI(api_key=st.secrets["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
            full_msgs = [{"role": "system", "content": PHYSICS_SYSTEM_PROMPT}] + st.session_state.messages + [{"role": "user", "content": prompt}]
            return client.chat.completions.create(model="deepseek-chat", messages=full_msgs, temperature=temperature).choices[0].message.content
    except Exception as e:
        return f"🚨 API Error: {str(e)}"

# --- 5. 核心动作处理 ---
def handle_action(action_text, input_type="ACTION", display_text=None):
    # 1. 记录用户输入
    prefix_map = {
        "ACTION": "【作死】",
        "QUIZ_ANSWER": "【答辩】",
        "REBUTTAL": "【卑微回复】"
    }
    user_content = display_text if display_text else f"{prefix_map.get(input_type, '')} {action_text}"
    st.session_state.messages.append({"role": "user", "content": user_content})
    
    # 只有常规动作才增加轮数
    if input_type == "ACTION":
        st.session_state.round_count += 1
    
    # 2. 预判逻辑：是否是第 4, 8, 12... 轮？
    force_quiz = False
    if input_type == "ACTION" and not st.session_state.is_over:
        if st.session_state.round_count > 0 and st.session_state.round_count % 4 == 0:
            force_quiz = True

    # 3. 构建 Prompt
    if input_type == "QUIZ_ANSWER":
        prompt = f"[ANSWER_QUIZ]: {action_text}。请评分，然后继续主线剧情，必须给出 A/B/C 三个选项。"
        st.session_state.mode = "NORMAL"
    
    elif input_type == "REBUTTAL":
        prompt = f"[GRADE: REBUTTAL]: {action_text}。请决定是接收还是拒稿，然后继续剧情，给出 A/B/C 选项。"
        st.session_state.mode = "NORMAL"
    
    else:
        if force_quiz:
            field = st.session_state.get("field", "物理")
            prompt = f"{action_text} (系统指令：本轮是第 {st.session_state.round_count} 轮，是**强制考核回合**。描述完动作后果后，**绝对不要**给出 A/B/C 选项。请直接使用标签 `[EVENT: QUIZ]` 并结合{field}领域出一道刁钻的简答题。)"
        else:
            prompt = f"{action_text} (请给出 A/B/C 三个选项)"

    # 4. AI 推演
    loading_text = {
        "NORMAL": "正在试图收敛...",
        "QUIZ": "导师正在推眼镜...",
        "BOSS": "Reviewer 2 正在磨刀..."
    }
    
    backend = st.session_state.get("backend_selection", "Google AI Studio (Gemini)")
    temperature = st.session_state.get("temperature_setting", 1.0)

    with st.spinner(loading_text.get(st.session_state.mode, "Loading...")):
        res = get_ai_response(prompt, backend, temperature)
    
    # 5. 解析回复
    new_mode = "NORMAL" 
    clean_res = res 
    
    # 结局检测
    if "[GAME_OVER:" in res:
        st.session_state.is_over = True
        st.session_state.final_report = re.sub(r"\[GAME_OVER:.*\]", "", res).strip()
        clean_res = st.session_state.final_report
        if "SUCCESS_ACADEMIC" in res: st.session_state.ending_type = "ACADEMIC"
        elif "SUCCESS_INDUSTRY" in res: st.session_state.ending_type = "INDUSTRY"
        else: st.session_state.ending_type = "FAILURE"
        
    # Boss 战检测
    elif "[EVENT: BOSS_BATTLE]" in res:
        new_mode = "BOSS"
        parts = res.split("[EVENT: BOSS_BATTLE]")
        clean_res = parts[0].strip()
        st.session_state.event_content = parts[1].strip()
        st.toast("⚠️ Reviewer 2 骑脸输出！", icon="⚔️")
        
    # 提问检测 (Quiz)
    elif "[EVENT: QUIZ]" in res:
        new_mode = "QUIZ"
        parts = res.split("[EVENT: QUIZ]")
        clean_res = parts[0].strip()
        if len(parts) > 1:
            st.session_state.event_content = parts[1].strip()
        else:
            st.session_state.event_content = "（系统错误：导师忘记出题了，但他依然看着你）"
        st.toast("⚠️ 考核回合：导师突袭！", icon="🚨")

    # 6. 存入历史并更新状态
    clean_res = clean_res.replace("[PLOT_DATA]", "").strip()
    if clean_res:
        st.session_state.messages.append({"role": "assistant", "content": clean_res})
    
    st.session_state.mode = new_mode

# --- 6. 侧边栏 ---
with st.sidebar:
    st.header("🎛️ 实验室控制台")
    st.session_state.backend_selection = st.selectbox("运算大脑:", ["DeepSeek", "Google AI Studio (Gemini)"])
    st.divider()
    
    st.session_state.temperature_setting = st.slider(
        "宇宙混沌常数 (Temperature)", 
        0.0, 1.5, 1.0, 0.1,
        help="🌡️ **熵增调节器**：\n\n"
             "🔹 **低数值 (0.1 - 0.5)**：\n"
             "物理定律严格，导师逻辑缜密，剧情偏向硬核现实主义（更像纪录片）。\n\n"
             "🔸 **高数值 (1.0 - 1.5)**：\n"
             "因果律崩坏，Reviewer 可能会提出用爱发电，剧情充满黑色幽默和荒诞感（更像瑞克和莫蒂）。"
    )
    
    st.write(f"当前轮次: **{st.session_state.round_count}**")
    if st.session_state.round_count > 0:
        if st.session_state.round_count % 4 == 0:
            st.warning("当前是：考核回合")
        else:
            st.info(f"距离下次考核还有：{4 - (st.session_state.round_count % 4)} 轮")

    days_left = 1460 - st.session_state.round_count * 7
    st.metric("距离延毕", f"{days_left} 天", delta="-1 周", delta_color="inverse")
    
    st.divider()
    st.write("☕ **摸鱼补给站:**")
    col1, col2 = st.columns(2)
    if col1.button("喝冰美式", help="精神熵 -10"):
        handle_action("【系统事件】玩家购买了冰美式。请降低精神熵，描述咖啡难喝。请给出 A/B/C 选项。", "ACTION", "【摸鱼】我喝了一杯刷锅水般的冰美式。")
        st.rerun()
    if col2.button("去海边发呆", help="导师杀意 +20"):
        handle_action("【系统事件】玩家去海边发呆。大幅降低精神熵，提升导师杀意。请给出 A/B/C 选项。", "ACTION", "【摸鱼】我去海边喂了会鸽子。")
        st.rerun()

    st.divider()
    if st.button("重开 (Re-roll)", type="primary"):
        st.session_state.clear()
        st.rerun()

# --- 7. 主界面渲染 (已修改标题) ---
st.title("⚗️ 物理学生存模拟：从入门到入土")

# --- 结局 UI ---
if st.session_state.is_over:
    if st.session_state.ending_type == "ACADEMIC":
        st.balloons()
        st.success("## 🏆 结局：学术界的一代宗师")
    elif st.session_state.ending_type == "INDUSTRY":
        st.balloons()
        st.info("## 💰 结局：半导体大厂的资本家")
    else:
        st.snow()
        st.error("## 🕯️ 结局：热力学寂灭 (退学)")
    st.markdown(f"> {st.session_state.final_report}")
    if st.button("投胎转世"): st.session_state.clear(); st.rerun()
    st.stop()

# --- 游戏正文 ---
if not st.session_state.game_started:
    col1, col2 = st.columns(2)
    with col1: role = st.radio("受难方向：", ["搬砖党 (实验)", "炼丹党 (理论)"])
    with col2: 
        field_input = st.text_input("请输入你的具体研究方向：", placeholder="例如：非厄米拓扑光子学 / 转角石墨烯 / 强关联电子体系...")
        st.session_state.field = field_input
    
    if st.button("签下卖身契 (Start)"):
        if not field_input:
            st.error("请先输入你的研究方向，否则导师不知道该骂你什么。")
        else:
            st.session_state.game_started = True
            real_prompt = f"我是{role}，研究{field_input}。请开启研究生生涯的第一天。请给出初始场景、初始数值和第一轮的选项。⚠️ 绝对不要直接给出结局，必须开始第一轮剧情。必须给出 A/B/C 三个选项。"
            display_prompt = f"【入学】我是{role}方向的研究生，研究{field_input}。我怀着激动（无知）的心情签下了卖身契。"
            handle_action(real_prompt, "ACTION", display_text=display_prompt)
            st.rerun()
else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    st.divider()

    # === 核心交互区域 ===
    
    # Mode 1: Boss Battle
    if st.session_state.mode == "BOSS":
        st.error("⚔️ **BOSS 战：Reviewer 2 正在骑脸输出！**")
        st.markdown(f"#### 审稿意见：\n{st.session_state.event_content}")
        st.caption("提示：请用最卑微的语气撰写 Rebuttal Letter。")
        if rebuttal := st.chat_input("撰写 Rebuttal..."):
            handle_action(rebuttal, "REBUTTAL")
            st.rerun()

    # Mode 2: Quiz (第 4, 8, 12... 轮固定触发)
    elif st.session_state.mode == "QUIZ":
        st.warning("🚨 **考核时刻：导师的死亡凝视**")
        st.markdown(f"#### {st.session_state.event_content}")
        if answer := st.chat_input("快编一个答案！"):
            handle_action(answer, "QUIZ_ANSWER")
            st.rerun()

    # Mode 3: Normal Options
    else:
        st.write("🔧 **抉择时刻：**")
        cols = st.columns(3)
        if cols[0].button("A", use_container_width=True): handle_action("A", "ACTION"); st.rerun()
        if cols[1].button("B", use_container_width=True): handle_action("B", "ACTION"); st.rerun()
        if cols[2].button("C", use_container_width=True): handle_action("C", "ACTION"); st.rerun()
        if prompt := st.chat_input("自定义作死操作..."):
            handle_action(prompt, "ACTION"); st.rerun()
