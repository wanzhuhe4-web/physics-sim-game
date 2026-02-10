import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import re

# --- 1. 页面配置 ---
st.set_page_config(page_title="物理学生存模拟：发量保卫战", page_icon="🎓", layout="wide")

# --- 2. 核心系统指令 ---
PHYSICS_SYSTEM_PROMPT = """
你是一款名为《物理学生存模拟：发量保卫战》的文字 RPG 引擎。
你的身份是**“学术界的墨菲定律化身”**。
你的语言风格：
1. **极度毒舌**：像那个总是卡你经费的行政人员，或者那个总是提刁钻问题的 Reviewer。
2. **物理隐喻**：用物理概念来形容生活。例如：“你的存款衰减得比 μ 子还快”、“导师的愤怒发生了蓝移（正在高速逼近）”。
3. **黑色幽默**：把惨剧说成喜剧。

# 核心数值 (每轮开头更新)
| 属性 | 当前值 | 物理学定义 |
| :--- | :--- | :--- |
| **头皮反光度** | 0% | 0%为茂密，100%为绝世强者。 |
| **精神熵** | Low | 达到“热寂”则退学。 |
| **导师杀意**| 0% | 达到 100% 触发“逐出师门”。 |
| **学术垃圾**| 0篇 | 毕业硬通货。 |

# 游戏模式与逻辑
1. **剧情模式**：根据玩家选择（A/B/C 或 自由输入）推进剧情，更新数值。
2. **提问模式 (Quiz Mode)**：
   - 当收到指令 `[GENERATE_QUIZ]` 时，请**忽略剧情推进**，直接根据玩家的研究领域（如强场物理/凝聚态），出一个极其硬核、刁钻的简答题。
   - 格式要求：以“### 导师的突然袭击：”开头。
3. **评分模式 (Grading Mode)**：
   - 当收到 `[ANSWER_QUIZ]: 玩家答案` 时，请以此评价玩家的物理水平。
   - **回答正确**：导师杀意大幅降低，奖励少量精神熵。
   - **回答错误/胡扯**：极尽嘲讽（如“你本科是在体校读的吗？”），头发掉落，杀意上升。

# 结局判定
- 标签：`[GAME_OVER: FAILURE]`, `[GAME_OVER: SUCCESS_ACADEMIC]`, `[GAME_OVER: SUCCESS_INDUSTRY]`。

# 任务
描述场景 -> [PLOT_DATA] (可选) -> 更新数值 -> 给出选项。
"""

# --- 4. 初始化状态 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.game_started = False
    st.session_state.is_over = False
    st.session_state.ending_type = None
    st.session_state.final_report = ""
    st.session_state.round_count = 0
    st.session_state.achievements = []
    # 新增：提问模式状态锁
    st.session_state.quiz_mode = False 
    st.session_state.quiz_content = ""

# --- 5. 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 实验室中控")
    backend = st.selectbox("运算大脑:", ["DeepSeek", "Google AI Studio (Gemini)"])
    st.divider()
    temperature = st.slider("宇宙混沌常数", 0.0, 1.5, 1.0, 0.1)
    st.metric("当前周数", f"第 {st.session_state.round_count} 周")
    
    st.write("🏆 **耻辱柱:**")
    for ach in st.session_state.achievements:
        st.success(ach)
            
    if st.button("重开一局 (Restart)", type="primary"):
        st.session_state.clear()
        st.rerun()

# --- 6. API 调用逻辑 ---
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

# --- 7. 核心动作处理 (状态机逻辑) ---
def handle_action(action_text, is_quiz_answer=False):
    # 1. 记录用户输入
    user_prefix = "[答辩]" if is_quiz_answer else "[操作]"
    st.session_state.messages.append({"role": "user", "content": f"{user_prefix} {action_text}"})
    
    # 如果不是回答问题，轮次+1
    if not is_quiz_answer:
        st.session_state.round_count += 1
    
    # 2. 构建 Prompt
    if is_quiz_answer:
        # 如果是回答问题，强制要求评分
        prompt = f"[ANSWER_QUIZ]: {action_text}。请评分并继续剧情。"
        st.session_state.quiz_mode = False # 退出提问模式
    else:
        prompt = action_text

    # 3. 获取 AI 回复
    with st.spinner("导师正在凝视你..." if st.session_state.quiz_mode else "系统推演中..."):
        res = get_ai_response(prompt)
    
    # 4. 处理绘图与标签
    plot_fig = None
    if "[PLOT_DATA]" in res or "数据" in res:
        status = "FAILURE" if ("失败" in res or "错误" in res) else "SUCCESS"
        plot_fig = generate_fake_plot(status)
    
    clean_res = re.sub(r"\[GAME_OVER:.*\]", "", res).replace("[PLOT_DATA]", "").strip()
    msg_obj = {"role": "assistant", "content": clean_res}
    if plot_fig: msg_obj["plot_status"] = "FAILURE" if ("失败" in res) else "SUCCESS"
    st.session_state.messages.append(msg_obj)

    # 5. 结局检测
    if "[GAME_OVER:" in res:
        st.session_state.is_over = True
        st.session_state.final_report = clean_res
        if "SUCCESS_ACADEMIC" in res: st.session_state.ending_type = "ACADEMIC"
        elif "SUCCESS_INDUSTRY" in res: st.session_state.ending_type = "INDUSTRY"
        else: st.session_state.ending_type = "FAILURE"
        return # 游戏结束，不再触发后续逻辑

    # === 6. 随机提问触发器 (核心修改) ===
    # 触发条件：
    # 1. 刚才不是在回答问题 (is_quiz_answer == False)
    # 2. 下一轮不是自由轮次 ( (round_count + 1) % 3 != 0 )
    # 3. 30% 概率触发
    next_is_free_round = (st.session_state.round_count + 1) % 3 == 0
    
    if not is_quiz_answer and not next_is_free_round and not st.session_state.is_over:
        if random.random() < 0.3: # 30% 概率突袭
            st.session_state.quiz_mode = True
            # 立即调用 AI 生成问题
            with st.spinner("⚠️ 检测到导师正在接近..."):
                quiz_res = get_ai_response(f"[GENERATE_QUIZ] 我现在的研究领域是：{st.session_state.field}。出一道简答题难住我。")
                st.session_state.quiz_content = quiz_res
                # 将问题存入历史，但不显示在上面的流中，而是显示在专用区域
                # st.session_state.messages.append({"role": "assistant", "content": quiz_res}) 
                # ^ 注释掉上面这行，避免重复显示，我们用 UI 独立渲染

# --- 8. 主界面渲染 ---
st.title("🎓 物理生存模拟：导师突袭版")

# --- 结局画面 ---
if st.session_state.is_over:
    if st.session_state.ending_type == "ACADEMIC":
        st.balloons()
        st.success("## 🏆 结局：学术界的一代宗师")
    elif st.session_state.ending_type == "INDUSTRY":
        st.balloons()
        st.info("## 💰 结局：半导体大厂的资本家")
    else:
        st.snow()
        st.error("## 🕯️ 结局：热力学寂灭")
    st.markdown(st.session_state.final_report)
    if st.button("投胎转世"): st.session_state.clear(); st.rerun()
    st.stop()

# --- 游戏正文 ---
if not st.session_state.game_started:
    col1, col2 = st.columns(2)
    with col1: role = st.radio("受难方向：", ["实验党", "理论党"])
    with col2: 
        field_input = st.text_input("具体天坑：", value="强场物理 / 凝聚态")
        st.session_state.field = field_input # 保存领域用于出题
    
    if st.button("开始献祭"):
        st.session_state.game_started = True
        handle_action(f"我是{role}，研究{field_input}。请开始我的受难。", is_quiz_answer=False)
        st.rerun()
else:
    # 渲染历史
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "plot_status" in msg:
                st.pyplot(generate_fake_plot(msg["plot_status"]))

    st.divider()

    # === 交互区域：三种模式互斥 ===
    
    # 1. 提问模式 (优先级最高)
    if st.session_state.quiz_mode:
        st.warning("🚨 **突发事件！导师把你堵在了茶水间！**")
        st.markdown(f"#### {st.session_state.quiz_content}")
        st.caption("提示：这可是关乎你发际线的关键时刻，好好回答。")
        
        if answer := st.chat_input("输入你的答案 (例如：因为波函数坍缩...)"):
            handle_action(answer, is_quiz_answer=True)
            st.rerun()

    # 2. 自由轮次 (每3轮触发)
    elif (st.session_state.round_count % 3 == 0) and (st.session_state.round_count > 0):
        st.info("✨ **自由意志时刻**：现在没人管你 (暂时的)。")
        if prompt := st.chat_input("输入你的疯狂计划..."):
            handle_action(prompt, is_quiz_answer=False)
            st.rerun()

    # 3. 常规轮次
    else:
        st.write("🔧 **实验室决策：**")
        cols = st.columns(3)
        if cols[0].button("A", use_container_width=True): handle_action("A", False); st.rerun()
        if cols[1].button("B", use_container_width=True): handle_action("B", False); st.rerun()
        if cols[2].button("C", use_container_width=True): handle_action("C", False); st.rerun()
        if prompt := st.chat_input("或输入自定义动作..."):
            handle_action(prompt, False); st.rerun()
        if prompt := st.chat_input("或输入回复测验的答案/自定义动作..."):
            handle_action(prompt)
            st.rerun()


