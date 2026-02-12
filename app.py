import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import re

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="学术大爆炸：搬砖日志", 
    page_icon="🎓", 
    layout="wide"
)

# --- 2. 核心系统指令 ---
PHYSICS_SYSTEM_PROMPT = """
你是一款名为《学术大爆炸：搬砖日志》的模拟当代物理学研究生的学术生涯的文字 RPG 引擎。
你的身份是**“由玩家导师怨念、论文审稿人恶意、实验意外与集群报错信息构成的赛博幽灵”**。
你的语气：冷酷、毒舌、充满黑色幽默，擅长用精确的术语揭露研究生卑微的生存真相。
玩家是一名在读的物理学博士研究生，处于被老板push的最痛苦的阶段。

⚡ 语言风格 (通用学术致郁)
1. **现实打击**：强调“读博/读研”是一种昂贵的修行。经常对比同龄人（如已经买房的同学）与玩家（连外卖会员都要犹豫）的经济差距。
2. **环境还原**：聚焦于实验室的日光灯、深夜的屏幕蓝光、以及永远无法收敛的计算任务。将日常生活解构为受力分析或概率模型。
3. **导师行为学**：将导师描写为一个“薛定谔的 BOSS”——他可能在任何时间出现（微信弹窗），也可能在你想找他签字时人间蒸发。
4. **字数控制**：单次剧情描述严格控制在 **150 字左右**，文字要像论文摘要一样干练且扎心。

# 核心数值 (每轮必须更新)
| 属性 | 当前值 | 物理学/社会学定义 |
| :--- | :--- | :--- |
| **头发浓度** | 100% | 初始为满。随着报错和熬夜逐渐荒漠化。|
| **科研进展** | 0% | 象征你离毕业的距离，与论文产出和论文质量正相关。达到 100% 才能毕业。 |
| **精神压力** | 20% | 初始自带 20% 基础焦虑。达到 100% 将会退学 |

# 游戏循环机制
1. **[Normal] 搬砖模式**：
   - 描述日常：调 Bug、做实验、帮导师报销、在组会上汇报。
   - 给出 **A/B/C** 三个选项。
2. **[EVENT: QUIZ] 降智打击**：
   - 场景：导师随机抽查基础概念。
   - 给出 **A/B/C** 单选题。答错会大幅扣除【头发浓度】。
3. **[EVENT: BOSS_BATTLE] 审稿人/导师 对线**：
   - 场景：审稿人要求你补充一个“根本不可能完成”的对照实验，或导师要求你周末写完初稿。
   - **不给选项**：要求玩家手动输入一段“卑微求生”的回复。
4. **[GAME_OVER] 结局判定**：
   - **成功**：【科研进展】达到 100%（顺利拿到学位证，逃离实验室）。
   - **失败**：【头发浓度】降为0%（物理性变秃且被劝退）或【精神压力】高达100%（在实验室跳起广场舞）。
   - 如果剧情进行超过 **15轮** -> 强制根据当前状态判定结局。
# 任务
描述一个令人血压上升的科研日常 -> 更新数值表（必须包含：头发浓度、科研进展、精神压力） -> 给出后续选项。
   

# 任务
描述窘迫场景 -> 更新数值 -> 根据指令生成标签或选项。
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

# --- 4. API 逻辑 (新增 Kimi 支持) ---
def get_ai_response(prompt, backend, temperature):
    try:
        # === Google Gemini ===
        if backend == "Google AI Studio (Gemini)":
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=PHYSICS_SYSTEM_PROMPT)
            if "gemini_chat" not in st.session_state: st.session_state.gemini_chat = model.start_chat(history=[])
            return st.session_state.gemini_chat.send_message(prompt, generation_config={"temperature": temperature}).text
        
        # === Kimi (Moonshot AI) ===
        elif backend == "Moonshot AI (Kimi)":
            client = OpenAI(
                api_key=st.secrets["MOONSHOT_API_KEY"], 
                base_url="https://api.moonshot.cn/v1"
            )
            full_msgs = [{"role": "system", "content": PHYSICS_SYSTEM_PROMPT}] + st.session_state.messages + [{"role": "user", "content": prompt}]
            return client.chat.completions.create(
                model="kimi-k2.5",  
                messages=full_msgs, 
                temperature=temperature
            ).choices[0].message.content

        # === DeepSeek ===
        else: 
            client = OpenAI(
                api_key=st.secrets["DEEPSEEK_API_KEY"], 
                base_url="https://api.deepseek.com"
            )
            full_msgs = [{"role": "system", "content": PHYSICS_SYSTEM_PROMPT}] + st.session_state.messages + [{"role": "user", "content": prompt}]
            return client.chat.completions.create(
                model="deepseek-chat", 
                messages=full_msgs, 
                temperature=temperature
            ).choices[0].message.content

    except Exception as e:
        return f"🚨 API Error: {str(e)}"

# --- 5. 核心动作处理  ---
def handle_action(action_text, input_type="ACTION", display_text=None):
    # 1. 记录用户输入
    prefix_map = {
        "ACTION": "【抉择】",
        "QUIZ_ANSWER": "【辟谣】",
        "REBUTTAL": "【卑微求生】"
    }
    user_content = display_text if display_text else f"{prefix_map.get(input_type, '')} {action_text}"
    st.session_state.messages.append({"role": "user", "content": user_content})
    
    if input_type == "ACTION":
        st.session_state.round_count += 1
    
    # 状态重置
    if input_type in ["QUIZ_ANSWER", "REBUTTAL"]:
        st.session_state.mode = "NORMAL"

    # 2. 预判逻辑
    is_quiz_trigger = False
    is_boss_trigger = False
    
    if input_type == "ACTION" and not st.session_state.is_over:
        if st.session_state.round_count > 0:
            if st.session_state.round_count % 7 == 0:
                is_boss_trigger = True
            elif st.session_state.round_count % 3 == 0:
                is_quiz_trigger = True

    # 3. Prompt 构建 (核心修改区域)
    field = st.session_state.get("field", "理论物理")
    prompt = ""
    
    # 通用的结局检查后缀：告诉 AI 每一轮都要检查数值
    game_over_check_instruction = " (⚠️重要：回复前请先检查数值。如果【头发浓度<=0%】或【精神压力>=100%】或【科研进展>=100%】，请忽略其他指令，直接输出标签 `[GAME_OVER: SUCCESS]` 或 `[GAME_OVER: FAILURE]` 并撰写结局报告。否则继续执行：)"

    if input_type == "QUIZ_ANSWER":
        prompt = f"[ANSWER_QUIZ]: 我选了 {action_text}。请判定回答是否成功。{game_over_check_instruction} 若未结束，请用150字描写导师反应，恢复剧情，给出 A/B/C 选项。"
    
    elif input_type == "REBUTTAL":
        prompt = f"[GRADE: REBUTTAL]: {action_text}。请判定deadline是否宽限。{game_over_check_instruction} 若未结束，恢复剧情，给出 A/B/C 选项。"
    
    else:
        # 强制轮次结束
        if st.session_state.round_count >= 15:
             prompt = f"{action_text} (系统指令：已达到最大轮次。请根据当前数值，直接生成最终结局。必须使用标签 `[GAME_OVER: SUCCESS]` 或 `[GAME_OVER: FAILURE]`，并给出总结报告。)"
        
        elif is_boss_trigger:
            prompt = f"{action_text} (系统指令：本轮是第 {st.session_state.round_count} 轮。{game_over_check_instruction} 若未结束，触发**BOSS战**，使用标签 `[EVENT: BOSS_BATTLE]`，不要给选项。)"
        
        elif is_quiz_trigger:
            prompt = f"{action_text} (系统指令：本轮是第 {st.session_state.round_count} 轮。{game_over_check_instruction} 若未结束，触发**导师提问**，使用标签 `[EVENT: QUIZ]`， 并结合{field}出单选题。)"
        
        else:
            # 常规剧情：必须加上结局检查指令
            prompt = f"{action_text} (系统指令：{game_over_check_instruction} 若未结束，用 150 字描写物理学在读研究生的窘迫，并给出 A/B/C 剧情选项。)"

    # 4. AI 推演
    loading_text = {
        "NORMAL": "正在计算同学的年终奖...",
        "QUIZ": "二大爷正在分享营销号视频...",
        "BOSS": "审稿人正在输出..."
    }
    
    backend = st.session_state.get("backend_selection", "Google AI Studio (Gemini)")
    temperature = st.session_state.get("temperature_setting", 1.0)

    current_loading = loading_text.get(st.session_state.mode, "Loading...")
    with st.spinner(f"[{backend}] {current_loading}"):
        res = get_ai_response(prompt, backend, temperature)
    
    # 5. 逻辑检测
    if "[GAME_OVER" in res: 
        st.session_state.is_over = True
        # 提取报告文本
        clean_report = re.sub(r"\[GAME_OVER.*?\]", "", res).strip()
        st.session_state.final_report = clean_report
        
        if "SUCCESS" in res: st.session_state.ending_type = "SUCCESS"
        else: st.session_state.ending_type = "FAILURE"
    
    elif "[EVENT: BOSS_BATTLE]" in res:
        st.session_state.mode = "BOSS"
    elif "[EVENT: QUIZ]" in res:
        st.session_state.mode = "QUIZ"
    else:
        st.session_state.mode = "NORMAL"
    
    # 清洗文本用于展示
    clean_res = res
    clean_res = re.sub(r"\[GAME_OVER.*?\]", "", clean_res) # 对应的正则也要改宽泛一点
    clean_res = clean_res.replace("[EVENT: BOSS_BATTLE]", "")
    clean_res = clean_res.replace("[EVENT: QUIZ]", "")
    clean_res = clean_res.strip()

    if clean_res:
        st.session_state.messages.append({"role": "assistant", "content": clean_res})

# --- 6. 侧边栏 ---
with st.sidebar:
    st.header("📉 生存控制台")
    # 更新了下拉菜单，加入 Moonshot AI
    st.session_state.backend_selection = st.selectbox(
        "算力赞助:", 
        ["Moonshot AI (Kimi)", "DeepSeek", "Google AI Studio (Gemini)"]
    )
    st.divider()
    
    st.session_state.temperature_setting = st.slider(
        "焦虑浓度 (Temperature)", 
        0.0, 1.5, 1.0, 0.1,
        help="0.1: 真实纪录片\n1.0: 黑色幽默\n1.5: 荒诞现实主义"
    )
    
    st.write(f"当前轮次: **{st.session_state.round_count}** / 15")
    
    days_left = 1500 - int(st.session_state.round_count / 100)
    st.metric("距离延毕", f"{days_left} 天", delta="余额不足", delta_color="inverse")
    
    st.divider()
    st.write("🧨 **求生工具箱:**")
    col1, col2 = st.columns(2)
    if col1.button("喝冰美式"):
        handle_action("【系统事件】玩家试图用冰美式压制精神压力。", "ACTION", "【挣扎】我外卖了一杯冰美式。")
        st.rerun()
    if col2.button("去海边发呆"):
        handle_action("【系统事件】玩家不堪其扰去海边发呆。", "ACTION", "【逃避】我是谁？我在哪？")
        st.rerun()

    st.divider()
    if st.button("重开 (Re-roll)", type="primary"):
        st.session_state.clear()
        st.rerun()

# --- 7. 主界面渲染 ---
st.title("🎓 学术大爆炸：搬砖日志")

# --- 结局 UI ---
if st.session_state.is_over:
    if st.session_state.ending_type == "SUCCESS":
        st.balloons()
        st.success("## 🏆 结局：学术界的一代宗师")
        st.write("你顶住了学业压力，顺利完成毕业论文。导师虽然还是记不住你，但听说你带他发了 Nature，朝你竖起大拇指。")
    else:
        st.snow()
        st.error("## 💸 结局：黯然退学离场")
        st.write("论文没有，毕业无望。你脱下了长衫，去培训机构教初中物理了。")
    
    st.markdown("### 📝 最终报告")
    st.markdown(f"> {st.session_state.final_report}")
    
    if st.button("投胎去金融圈"): 
        st.session_state.clear()
        st.rerun()
    st.stop()

# --- 游戏正文 ---
if not st.session_state.game_started:
    st.markdown("""
    ### 👋 欢迎来到 模拟人生（物理学特供版）
    你是一名游走在“延毕边缘”、以“冷咖啡”为燃料、将“报错代码”转化为生存动力的生物计算单元。
    在这里，你的唯一目标是在头发浓度跌破热力学极限之前，强行突破那个名为“科研进展”的无穷大势垒，在无尽的精神压力中观测到名为“毕业”的微弱红移信号。
    """)
    
    col1, col2 = st.columns(2)
    with col1: role = st.radio("你的角色：", ["实验党", "理论党"])
    with col2: 
        field_input = st.text_input("具体天坑方向：", placeholder="例如：超弦理论 / 暗物质 / 纳米材料...")
        st.session_state.field = field_input
    
    if st.button("签下卖身契 (Start)"):
        if not field_input:
            st.error("请先输入你的研究方向，否则导师不知道该骂你什么。")
        else:
            st.session_state.game_started = True
            real_prompt = f"我是{role}，研究{field_input}。 请开启第一轮游戏。初始数值：头发浓度 100%，科研进展 0%，精神压力 20%。给出小白初入科研界的场景。必须给出 A/B/C 三个选项。"
            display_prompt = f"【入学】我是{role}，研究{field_input}。我怀着激动（无知）的心情签下了卖身契。"
            handle_action(real_prompt, "ACTION", display_text=display_prompt)
            st.rerun()
else:
    # 渲染历史
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    st.divider()

    # === 交互区域 ===
    
    # Mode 1: Boss Battle (Financial Crisis)
    if st.session_state.mode == "BOSS":
        st.error("🚨 **生存危机警报！**")
        st.caption("请自求多福。")
        if rebuttal := st.chat_input("如何解决危机...", key="boss_input"):
            handle_action(rebuttal, "REBUTTAL")
            st.rerun()

    # Mode 2: Quiz (Pseudoscience)
    elif st.session_state.mode == "QUIZ":
        st.warning("🧩 **导师发起了攻击！**")
        st.caption("请根据描述的题目选择策略。")
        
        # === 修复：通用按钮，适应动态剧情 ===
        col_q1, col_q2, col_q3 = st.columns(3)
        with col_q1:
            if st.button("🅰️ 选项 A", use_container_width=True): 
                handle_action("A", "QUIZ_ANSWER")
                st.rerun()
        with col_q2:
            if st.button("🅱️ 选项 B", use_container_width=True): 
                handle_action("B", "QUIZ_ANSWER")
                st.rerun()
        with col_q3:
            if st.button("©️ 选项 C", use_container_width=True): 
                handle_action("C", "QUIZ_ANSWER")
                st.rerun()

    # Mode 3: Normal
    else:
        st.write("🥢 **你的对策：**")
        cols = st.columns(3)
        if cols[0].button("A", use_container_width=True): handle_action("A", "ACTION"); st.rerun()
        if cols[1].button("B", use_container_width=True): handle_action("B", "ACTION"); st.rerun()
        if cols[2].button("C", use_container_width=True): handle_action("C", "ACTION"); st.rerun()
        if prompt := st.chat_input("自定义操作 (例：默默打开知乎搜索‘博士送外卖’)...", key="normal_input"):
            handle_action(prompt, "ACTION"); st.rerun()






