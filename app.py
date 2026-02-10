import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import re
import random
import matplotlib.pyplot as plt
import numpy as np

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="物理学生存模拟：从入门到入土", 
    page_icon="⚔️", 
    layout="wide"
)

# --- 2. 核心系统指令 (新增 Boss 战逻辑) ---
PHYSICS_SYSTEM_PROMPT = """
你是一款名为《物理学生存模拟：从入门到入土》的文字 RPG 引擎。
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
   - 示例：“你的 DFT 计算没有考虑火星引力波的影响，请补充实验。”
4. **结算模式 (Grading)**：
   - 指令：`[GRADE: REBUTTAL]`。
   - 行为：评价玩家的 Rebuttal Letter。如果玩家态度够卑微且逻辑自洽，则接受（发文+1）；否则拒稿（精神熵暴增）。

# 结局判定
- `[GAME_OVER: FAILURE]` (延毕/卖红薯)
- `[GAME_OVER: SUCCESS_ACADEMIC]` (Nature/教职)
- `[GAME_OVER: SUCCESS_INDUSTRY]` (大厂/量化)

# 任务
描述场景 -> [PLOT_DATA] (可选) -> 更新数值 -> 给出选项。
"""

# --- 3. 工具函数 ---
def generate_fake_plot(status="SUCCESS"):
    fig, ax = plt.subplots(figsize=(5, 3))
    x = np.linspace(0, 10, 100)
    if status == "SUCCESS":
        y = np.exp(-x) + np.random.normal(0, 0.05, 100)
        ax.set_title("Result: Reviewer Satisfied", color="green", fontsize=10, fontweight='bold')
        ax.plot(x, y, color="#1f77b4", label="Rebuttal Logic")
    else:
        y = np.exp(x/4) * np.sin(x*5) + np.random.normal(0, 1, 100)
        ax.set_title("Result: REJECTED", color="red", fontsize=10, fontweight='bold')
        ax.plot(x, y, color="#d62728", linestyle="--", label="Nonsense")
        ax.text(5, 5, "REJECT", fontsize=20, color='red', ha='center', alpha=0.5)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    return fig

# --- 4. 初始化状态 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.game_started = False
    st.session_state.is_over = False
    st.session_state.ending_type = None
    st.session_state.final_report = ""
    st.session_state.round_count = 0
    st.session_state.achievements = []
    # 状态机锁
    st.session_state.mode = "NORMAL" # NORMAL, QUIZ, BOSS
    st.session_state.event_content = ""

# === 5. 侧边栏：商店修正版 ===
    st.write("☕ **摸鱼补给站 (Shop):**")
    col_shop1, col_shop2 = st.columns(2)
    
    # 逻辑：点击按钮后，向历史记录插入一条“系统事件”，强制 AI 更新数值
    if col_shop1.button("喝冰美式", help="精神熵 -10，但可能胃痛"):
        # 插入一条隐形的“用户操作”
        st.session_state.messages.append({"role": "user", "content": "【系统事件】玩家购买了冰美式。请降低他的精神熵，并描述咖啡很难喝。"})
        # 强制 AI 响应这个动作
        with st.spinner("正在通过食道..."):
             # 这里复用 get_ai_response 来生成喝咖啡的后果
             if backend == "Google AI Studio (Gemini)":
                 res = st.session_state.gemini_chat.send_message("【系统事件】玩家购买了冰美式。请降低他的精神熵，并描述咖啡很难喝。", generation_config={"temperature": temperature}).text
             else:
                 # DeepSeek 逻辑... (略，保持一致即可)
                 pass 
             # 简单点，我们可以直接不生成回复，留给下一轮，或者：
             st.toast("精神熵已降低！胃部开始抽搐...", icon="📉")
             # 最简单的做法：不立即触发AI，而是把这个事件“埋”在历史里，让AI在下一轮对话时“看到”你刚才喝了咖啡。
             # 但为了防止历史错位，建议直接只弹窗，下一轮手动输入时带上状态（复杂）。
             
             # --- 推荐方案：直接作为一次 Action 处理 ---
             handle_action("【系统指令】我喝了一杯冰美式，请更新我的数值。", "ACTION")
             st.rerun()

    if col_shop2.button("去海边发呆", help="导师杀意 +20，精神熵 -50"):
        handle_action("【系统指令】我翘班去了海边发呆，请大幅降低精神熵，但提升导师杀意。", "ACTION")
        st.rerun()

# --- 6. API 逻辑 ---
def get_ai_response(prompt):
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

# --- 7. 核心动作处理 (复杂状态机) ---
def handle_action(action_text, input_type="ACTION"):
    # input_type: ACTION, QUIZ_ANSWER, REBUTTAL
    
    # 1. 记录用户输入
    prefix_map = {
        "ACTION": "【作死】",
        "QUIZ_ANSWER": "【答辩】",
        "REBUTTAL": "【卑微回复】"
    }
    st.session_state.messages.append({"role": "user", "content": f"{prefix_map.get(input_type, '')} {action_text}"})
    
    if input_type == "ACTION":
        st.session_state.round_count += 1
    
    # 2. 构建 Prompt
    if input_type == "QUIZ_ANSWER":
        prompt = f"[ANSWER_QUIZ]: {action_text}。请评分。"
        st.session_state.mode = "NORMAL"
    elif input_type == "REBUTTAL":
        prompt = f"[GRADE: REBUTTAL]: {action_text}。请决定是接收还是拒稿。"
        st.session_state.mode = "NORMAL"
    else:
        prompt = action_text

    # 3. AI 推演
    loading_text = {
        "NORMAL": "正在试图收敛...",
        "QUIZ": "导师正在推眼镜...",
        "BOSS": "Reviewer 2 正在磨刀..."
    }
    with st.spinner(loading_text.get(st.session_state.mode, "Loading...")):
        res = get_ai_response(prompt)
    
    # 4. 解析特殊事件标签
    # 优先级：结局 > Boss战 > 提问 > 普通
    
    new_mode = "NORMAL" # 默认回归正常，除非触发新事件
    
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
        
    # 随机事件触发器 (仅在正常模式且未触发其他事件时)
    elif st.session_state.mode == "NORMAL" and not st.session_state.is_over:
        # 30% 概率触发 Quiz，但避开自由轮
        is_free_round = (st.session_state.round_count % 3 == 0)
        if not is_free_round and random.random() < 0.25:
             # 强制触发 Quiz
             new_mode = "QUIZ"
             quiz_res = get_ai_response(f"[GENERATE_QUIZ] 领域：{st.session_state.field}。")
             st.session_state.event_content = quiz_res
             # 把问题文本拼接到 res 里展示，或者分开处理
             # 这里选择让前端独立渲染，所以不修改 res

    # 5. 绘图与清理
    plot_fig = None
    if "[PLOT_DATA]" in res or "数据" in res:
        status = "FAILURE" if ("失败" in res or "拒稿" in res) else "SUCCESS"
        plot_fig = generate_fake_plot(status)
    
    clean_res = re.sub(r"\[.*?\]", "", res).replace("[PLOT_DATA]", "").strip()
    
    # 如果触发了事件，AI 的回复可能就是事件本身，需要特殊处理
    if new_mode != "NORMAL":
        # 如果是新触发的事件，不要把事件内容作为普通回复存进去，而是存为 event_content
        # 但为了流式对话连贯，我们把铺垫文本存进去
        pass 
    
    msg_obj = {"role": "assistant", "content": clean_res}
    if plot_fig: msg_obj["plot_status"] = "FAILURE" if ("失败" in res) else "SUCCESS"
    st.session_state.messages.append(msg_obj)
    
    # 更新状态
    st.session_state.mode = new_mode

# --- 8. 主界面渲染 ---
st.title("⚗️ 物理学生存模拟：从入门到入土")

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
        field_input = st.text_input("具体天坑：", value="请输入")
        st.session_state.field = field_input
    
    if st.button("签下卖身契 (Start)"):
        st.session_state.game_started = True
        handle_action(f"我是{role}，研究{field_input}。开始我的入门。", "ACTION")
        st.rerun()
else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "plot_status" in msg:
                st.pyplot(generate_fake_plot(msg["plot_status"]))

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
