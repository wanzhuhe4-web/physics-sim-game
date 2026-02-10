import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import re
import random

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="物理博士生存模拟：从入门到入土", 
    page_icon="⚗️", 
    layout="wide"
)

# --- 2. 核心系统指令 (修复选项格式问题) ---
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

# 游戏模式状态机
1. **剧情模式 (Normal)**：推进剧情，极尽嘲讽。
2. **提问模式 (Quiz)**：导师突袭查岗。触发指令 `[EVENT: QUIZ]`。
3. **BOSS 战模式 (Reviewer Battle)**：
   - 触发条件：玩家进行“投稿”或随机触发。
   - 指令：`[EVENT: BOSS_BATTLE]`。
   - 行为：扮演 **Reviewer 2**。提出 2-3 条极其荒谬、自相矛盾、吹毛求疵的审稿意见。
4. **结算模式 (Grading)**：
   - 指令：`[GRADE: REBUTTAL]`。
   - 行为：评价玩家的 Rebuttal Letter。如果玩家态度够卑微且逻辑自洽，则接受（发文+1）；否则拒稿（精神熵暴增）。

# 结局判定
- `[GAME_OVER: FAILURE]` (延毕/卖红薯)
- `[GAME_OVER: SUCCESS_ACADEMIC]` (Nature/教职)
- `[GAME_OVER: SUCCESS_INDUSTRY]` (大厂/量化)

# ⚠️ 游戏节奏控制 (关键规则)
1. **绝对禁止**在前 5 轮内强制触发结局。
2. 游戏必须是**回合制**的。
3. **不要**一次性生成整个职业生涯的故事。

# ⚠️ 格式强制要求 (UI 适配)
每次回复的最后，必须给出**严格且仅有**的三个选项，并使用 **A、B、C** 作为编号。
格式示例：
A. 选项一内容...
B. 选项二内容...
C. 选项三内容...
(绝对不要使用 1/2/3/4 编号，也不要给出第 4 个选项)

# 任务
描述场景 -> 更新数值 -> 给出 A/B/C 选项。
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
    """
    action_text: 发送给 AI 的实际内容（包含指令）
    input_type: 动作类型
    display_text: (可选) 显示在聊天界面上的精简内容。如果为 None，则显示 action_text。
    """
    
    # 1. 记录用户输入 (UI 显示层)
    prefix_map = {
        "ACTION": "【作死】",
        "QUIZ_ANSWER": "【答辩】",
        "REBUTTAL": "【卑微回复】"
    }
    
    if display_text:
        user_content = display_text
    else:
        user_content = f"{prefix_map.get(input_type, '')} {action_text}"
        
    st.session_state.messages.append({"role": "user", "content": user_content})
    
    if input_type == "ACTION":
        st.session_state.round_count += 1
    
    # 2. 构建 Prompt (AI 逻辑层)
    if input_type == "QUIZ_ANSWER":
        prompt = f"[ANSWER_QUIZ]: {action_text}。请评分。"
        st.session_state.mode = "NORMAL"
    elif input_type == "REBUTTAL":
        prompt = f"[GRADE: REBUTTAL]: {action_text}。请决定是接收还是拒稿。"
        st.session_state.mode = "NORMAL"
    else:
        # 在这里再次强调格式，防止 AI 忘掉
        prompt = f"{action_text} (请给出 A/B/C 三个选项)"

    # 3. AI 推演
    loading_text = {
        "NORMAL": "正在试图收敛...",
        "QUIZ": "导师正在推眼镜...",
        "BOSS": "Reviewer 2 正在磨刀..."
    }
    
    backend = st.session_state.get("backend_selection", "Google AI Studio (Gemini)")
    temperature = st.session_state.get("temperature_setting", 1.0)

    with st.spinner(loading_text.get(st.session_state.mode, "Loading...")):
        res = get_ai_response(prompt, backend, temperature)
    
    # 4. 解析特殊事件标签
    new_mode = "NORMAL" 
    
    if "[GAME_OVER:" in res:
        st.session_state.is_over = True
        st.session_state.final_report = re.sub(r"\[GAME_OVER:.*\]", "", res).strip()
        if "SUCCESS_ACADEMIC" in res: st.session_state.ending_type = "ACADEMIC"
        elif "SUCCESS_INDUSTRY" in res: st.session_state.ending_type = "INDUSTRY"
        else: st.session_state.ending_type = "FAILURE"
        
    elif "[EVENT: BOSS_BATTLE]" in res:
        new_mode = "BOSS"
        st.session_state.event_content = re.sub(r"\[EVENT:.*\]", "", res).strip()
        st.toast("⚠️ 警告：Reviewer 2 出现了！", icon="⚔️")
        
    elif "[EVENT: QUIZ]" in res:
        new_mode = "QUIZ"
        st.session_state.event_content = re.sub(r"\[EVENT:.*\]", "", res).strip()
        st.toast("⚠️ 警告：导师发起突袭！", icon="🚨")
        
    # 随机事件触发器 (30%概率，且避开自由轮)
    elif st.session_state.mode == "NORMAL" and not st.session_state.is_over:
        is_free_round = (st.session_state.round_count % 3 == 0)
        if not is_free_round and random.random() < 0.2:
             new_mode = "QUIZ"
             quiz_res = get_ai_response(f"[GENERATE_QUIZ] 领域：{st.session_state.field}。", backend, temperature)
             st.session_state.event_content = quiz_res

    # 5. 清理回复中的标签
    clean_res = re.sub(r"\[.*?\]", "", res).replace("[PLOT_DATA]", "").strip()
    st.session_state.messages.append({"role": "assistant", "content": clean_res})
    
    # 更新状态
    st.session_state.mode = new_mode

# --- 6. 侧边栏：商店与中控 ---
with st.sidebar:
    st.header("🎛️ 实验室控制台")
    st.session_state.backend_selection = st.selectbox("运算大脑:", ["DeepSeek", "Google AI Studio (Gemini)"])
    
    st.divider()
    st.session_state.temperature_setting = st.slider("宇宙混沌常数 (Temperature)", 0.0, 1.5, 1.0, 0.1, help="拉得越高，导师越疯。")
    
    days_left = 1460 - st.session_state.round_count * 7
    st.metric("距离延毕", f"{days_left} 天", delta="-1 周", delta_color="inverse")
    
    st.divider()
    st.write("☕ **摸鱼补给站 (Shop):**")
    col_shop1, col_shop2 = st.columns(2)
    
    if col_shop1.button("喝冰美式", help="精神熵 -10"):
        handle_action(
            action_text="【系统事件】玩家购买了冰美式。请降低他的精神熵，并描述咖啡很难喝。请给出 A/B/C 选项。", 
            input_type="ACTION",
            display_text="【摸鱼】我喝了一杯刷锅水般的冰美式，感觉活过来了。"
        )
        st.rerun()

    if col_shop2.button("去海边发呆", help="导师杀意 +20"):
        handle_action(
            action_text="【系统事件】玩家翘班去了海边发呆。请大幅降低精神熵，但提升导师杀意。请给出 A/B/C 选项。", 
            input_type="ACTION",
            display_text="【摸鱼】我去巴勒莫的海边喂了会鸽子，手机关机了。"
        )
        st.rerun()

    st.divider()
    if st.button("重开 (Re-roll)", type="primary"):
        st.session_state.clear()
        st.rerun()

# --- 7. 主界面渲染 ---
st.title("⚗️ 物理博士生存模拟：从入门到入土")

# --- 结局 UI ---
if st.session_state.is_over:
    if st.session_state.ending_type == "ACADEMIC":
        st.balloons()
        st.success("## 🏆 结局：学术界的一代宗师")
        st.image("https://img.icons8.com/color/96/trophy.png", width=100)
    elif st.session_state.ending_type == "INDUSTRY":
        st.balloons()
        st.info("## 💰 结局：半导体大厂的资本家")
        st.image("https://img.icons8.com/color/96/money-bag.png", width=100)
    else:
        st.snow()
        st.error("## 🕯️ 结局：热力学寂灭 (退学)")
        st.image("https://img.icons8.com/color/96/crying.png", width=100)
    st.markdown(f"> {st.session_state.final_report}")
    if st.button("投胎转世"): st.session_state.clear(); st.rerun()
    st.stop()

# --- 游戏正文 ---
if not st.session_state.game_started:
    col1, col2 = st.columns(2)
    with col1: role = st.radio("受难方向：", ["搬砖党 (实验)", "炼丹党 (理论)"])
    with col2: 
        field_input = st.text_input("具体天坑：", value="强场物理 / 凝聚态")
        st.session_state.field = field_input
    
    
    
    if st.button("签下卖身契 (Start)"):
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

    # === 核心交互区域 (根据 Mode 渲染不同 UI) ===
    
    # Mode 1: Boss Battle (Reviewer)
    if st.session_state.mode == "BOSS":
        st.error("⚔️ **BOSS 战：Reviewer 2 正在骑脸输出！**")
        if st.session_state.event_content:
            st.markdown(f"#### 审稿意见：\n{st.session_state.event_content}")
        else:
            st.markdown("#### 审稿人发来了一封全是全大写字母的邮件...")
            
        st.caption("提示：请用最卑微的语气，解释为什么你的图 3 不是用画图板画的。")
        if rebuttal := st.chat_input("撰写 Rebuttal Letter (Example: 尊敬的 Reviewer 大佬...)"):
            handle_action(rebuttal, "REBUTTAL")
            st.rerun()

    # Mode 2: Quiz (Mentor)
    elif st.session_state.mode == "QUIZ":
        st.warning("🚨 **突发事件：导师的死亡凝视**")
        if st.session_state.event_content:
            st.markdown(f"#### {st.session_state.event_content}")
        
        if answer := st.chat_input("快编一个答案！"):
            handle_action(answer, "QUIZ_ANSWER")
            st.rerun()

    # Mode 3: Free Action (Every 3 Rounds)
    elif (st.session_state.round_count % 3 == 0) and (st.session_state.round_count > 0):
        st.info("✨ **自由意志时刻 (Free Action)**")
        st.caption("实验室没人！你可以做任何事。")
        if prompt := st.chat_input("输入你的疯狂计划..."):
            handle_action(prompt, "ACTION")
            st.rerun()

    # Mode 4: Normal
    else:
        st.write("🔧 **抉择时刻：**")
        cols = st.columns(3)
        if cols[0].button("A", use_container_width=True): handle_action("A", "ACTION"); st.rerun()
        if cols[1].button("B", use_container_width=True): handle_action("B", "ACTION"); st.rerun()
        if cols[2].button("C", use_container_width=True): handle_action("C", "ACTION"); st.rerun()
        
        if prompt := st.chat_input("自定义作死操作..."):
            handle_action(prompt, "ACTION"); st.rerun()
