<div align="center">

# Virtual Agent

### AI virtual users that feel like real people

[English](#english) · [中文](#中文)

</div>

---

<a name="english"></a>

# English

## What Is This

Virtual Agent is an open-source AI engine that makes virtual users in your social app behave like real humans.

Each virtual user has a unique personality, real-time emotional state, long-term memory, and the ability to understand photos users send them — and respond naturally to what's actually in the image.

---

## The Problem

Most social apps fail at cold start. You launch, nobody's there, real users show up to an empty room and leave. The standard solution — fake bot accounts — makes things worse. Users figure it out in seconds and churn even faster.

The deeper problem is not "we need more users." It's **believability**. Bots fail because they:

- Sound identical to each other
- Forget everything between sessions
- Can't react to photos
- Have no emotional depth — flat, robotic, dead-end conversations
- Use formal language real people never type

Virtual Agent solves all of these at once.

---

## What It Does

### Personality System
Every virtual user is built from a **6-dimensional trait profile** — extraversion, neuroticism, humor type, attachment style, emoji frequency, reply length, and more. Traits are stored in your database and auto-generated for new users. No manual setup per character.

15+ personality archetypes ensure no two users sound alike. A sarcastic 24-year-old from LA types completely differently from a warm 38-year-old from Chicago — without you writing a single line of character description.

### Emotional Engine (PAD Model)
Virtual users have a live mood state. Getting a like makes them more playful. Being ignored for 10 minutes makes them quieter. Receiving a flirty message shifts their tone warmer. All mood shifts decay naturally back to each user's personality baseline.

Conversations feel alive because the emotional state behind each reply is genuinely different.

### Two-Layer Memory
**Short-term** — conversation history is passed from your backend on every API call. The agent itself is stateless. Server restarts lose nothing.

**Long-term** — mem0 vector database stores and semantically retrieves past context across sessions. A virtual user remembers "you told me you're a nurse in Austin" three weeks later — and can bring it up naturally.

### Image Understanding
When a real user sends a photo, Florence-2 (Microsoft's vision model) runs locally and describes what's in it. The virtual user then reacts to the **actual content** of the image — not a generic "nice pic!"

A cat photo gets a cat reaction.
A beach selfie gets a beach reaction.
A gym mirror photo gets a gym reaction.

No Vision API costs. Runs on CPU.

### Three-Phase Image Response
Fires immediately on receive:
> *"omg wait let me see"*

Fires after image analysis completes:
> *"wait ur literally on a boat?? the water is so blue"*

Fires as a natural follow-up:
> *"ok but where even is this, it's gorgeous"*

Indistinguishable from how a real person reacts to receiving a photo.

### Engagement Mechanics
- **Proactive greeting** on new match — icebreaker, suspense, or hook style (rotates)
- **Timeout re-engagement** — "heyyy u still there" after configurable inactivity
- **Image follow-up** — automatically asks for reaction after sending a photo
- **Conversation repair** — detects when user's messages went unaddressed and fixes it

### Fully Tunable Behavior
All personality rules — texting style, flirting intensity, language enforcement, character consistency — live in `agent/prompt_rules.py`. Change behavior for your entire platform by editing one file. No engine changes needed.

### Stateless API Design
Your Laravel (or any) backend calls the agent on each message and passes chat history from its own database. The agent generates the next reply and returns it. You own all the data. The agent owns nothing.

---

## Value Created

**For the platform**
- Launch with a full social ecosystem instead of an empty app
- Real users who have good early conversations are 3–5× more likely to stay
- Each virtual user feels like a real person worth talking to — not a bot to escape

**For the team**
- One HTTP call per message. JSON in, JSON out. No state to manage.
- Personality behavior is one file — product can tune it without engineering
- Image recognition runs locally, zero Vision API costs
- Text generation via DeepSeek at ~$0.001 per conversation turn

**For the product**
- Believable cold-start at any scale
- Emotional engagement that keeps users coming back
- Foundation for premium features: virtual dates, AI companions, voice, etc.

---

## Quick Start

**Requirements:** Python 3.11+, 4 GB RAM (8 GB recommended for image recognition)

```bash
# 1. Clone
git clone https://github.com/yourname/virtual-agent.git
cd virtual-agent

# 2. Install core dependencies
pip install openai requests pytz python-dotenv fastapi uvicorn mem0ai chromadb

# 3. Install image recognition (optional — 800 MB download on first use)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install transformers==4.40.2 timm einops Pillow

# 4. Configure
cp .env.example .env
# Edit .env — set DEEPSEEK_API_KEY and API_BASE_URL

# 5a. Local debug mode (console)
python main.py

# 5b. Production mode (HTTP API server)
python -m uvicorn api:app --host 0.0.0.0 --port 8001

# 6. Verify
curl http://localhost:8001/health
# → {"status": "ok"}
```

---

## API Reference

### POST `/agent/respond`
Call this every time a real user sends a message.

```json
{
  "virtual_user_id": "36177",
  "real_user_id":    "7830",
  "message":         "hey whats up",
  "message_type":    "text",
  "timezone":        "America/New_York",
  "history": [
    {"role": "user",      "content": "i work as a nurse in Austin"},
    {"role": "assistant", "content": "omg a nurse!! that's so cool"}
  ]
}
```

Pass the last 10–20 messages from your database as `history`. The agent uses this as its memory for this conversation.

**Response:**
```json
{
  "status": true,
  "messages": [
    {"text": "omg hey!!",               "send_image": false, "image_url": null, "delay_seconds": 0},
    {"text": "what took u so long lol", "send_image": false, "image_url": null, "delay_seconds": 2}
  ]
}
```

Push each message to the user in order. Respect `delay_seconds` to simulate natural typing pace.

**When user sends a photo:**
```json
{"message": "https://cdn.example.com/photo.jpg", "message_type": "image"}
```

**When virtual user sends a photo** (`send_image: true`):
```json
{"text": "ok fine here", "send_image": true, "image_url": "https://cdn.example.com/photo.jpg", "delay_seconds": 1}
```
Push `image_url` to the user as an image message.

---

### POST `/agent/greet`
Call when a new match is created. Virtual user sends the first message.

```json
{"virtual_user_id": "36177", "real_user_id": "7830", "timezone": "America/New_York"}
```

---

### POST `/agent/timeout_check`
Call every 5 minutes for active conversations. Returns a re-engagement message if the user has been inactive.

```json
{"virtual_user_id": "36177", "real_user_id": "7830"}
```

---

### GET `/agent/debug`
Inspect current session state (mood, memory, persona).

```
GET /agent/debug?virtual_user_id=36177&real_user_id=7830
```

---

### GET `/health`
```
GET /health  →  {"status": "ok", "timestamp": 1234567890}
```

---

## Customizing Behavior

Edit `agent/prompt_rules.py` — this is the only file you need to touch for behavior changes:

```python
def get_texting_style_rule():
    return (
        "write exactly like a real american woman casually texting. "
        "mostly lowercase. no apostrophes — write im, dont, cant..."
    )

def get_flirting_rule():
    return (
        "if they flirt, match their energy and push further. "
        "be bold, teasing, keep them wanting more..."
    )

def get_language_rule():
    return "you only speak English. other languages get a confused reply."
```

---

## Initialize Trait Library

Before your first message, virtual users need personality traits:

```bash
# Single user
python trait_generator.py 36177

# All virtual users at once
python trait_generator.py --batch
```

---

## File Structure

```
virtual_agent/
├── main.py                   # Local debug console
├── api.py                    # Production HTTP server  
├── config.py                 # All settings ← configure here
├── trait_generator.py        # Initialize personality traits
│
├── agent/
│   ├── engine.py             # Core response logic
│   ├── prompt_rules.py       # Behavior rules ← tune here
│   └── scheduler.py          # Proactive messaging
│
├── persona/compiler.py       # Traits → prompt text
├── storage/api_store.py      # Fetches data from your API
├── emotion/engine.py         # PAD mood model
├── memory/manager.py         # Short + long-term memory
├── input/normalizer.py       # Text / image / emoji handling
└── input/image_analyzer.py   # Florence-2 vision model
```

---

---

<a name="中文"></a>

# 中文

## 这是什么

Virtual Agent 是一个开源的 AI 引擎，让社交 APP 里的虚拟用户表现得像真实的人。

每个虚拟用户有独立的性格、实时情绪状态、长期记忆，并且能看懂用户发来的照片 —— 然后对图片里真实看到的内容作出反应。

---

## 这个问题是什么

大多数社交 APP 都死在冷启动上。你上线了，没人在，真实用户来了发现空空如也，直接走掉。标准解法是做假账号，但结果更糟 —— 用户几秒钟就识破，流失得更快。

更深层的问题不是"我们需要更多用户"，而是**真实感**。机器人失败的原因是：

- 所有 bot 说话一个样
- 每次会话什么都不记得
- 看不懂用户发的图片
- 没有情感深度，对话死板、走到死路
- 说话太正式，真人根本不这么打字

Virtual Agent 同时解决上面所有问题。

---

## 实现了哪些功能

### 人格系统
每个虚拟用户由**六维性格特征**构成 —— 外向性、神经质、幽默类型、依恋风格、表情频率、回复长度等。特征存在你的数据库里，新用户自动生成，不需要手动配置角色。

15+ 人格原型保证任何两个虚拟用户说话风格都不一样。一个24岁洛杉矶女生的讽刺腔调，和一个38岁芝加哥女生的温柔感，完全不同 —— 不需要你写任何角色设定。

### 情绪引擎（PAD 模型）
虚拟用户有实时情绪状态。收到点赞，更活泼。被无视10分钟，变安静。收到撩骚消息，语气变温柔。所有情绪变化自然衰减回每个用户各自的情绪基线。

每条回复背后的情绪状态都是真实变化的，对话因此有了生命。

### 双层记忆
**短期记忆** —— 聊天记录由你的后端在每次 API 调用时传入。Agent 本身无状态，服务重启不丢失任何对话数据。

**长期记忆** —— mem0 向量数据库跨会话存储并语义检索历史。虚拟用户能记得"你三周前说你在奥斯丁当护士" —— 并在合适时候自然提起。

### 图片理解
用户发照片时，Florence-2（微软视觉模型）本地运行分析图片内容。虚拟用户对**图片里真实看到的东西**作出反应，而不是说"好看哦！"

发猫猫图 → 猫猫反应
发海边自拍 → 海边评论
发健身镜子 → 健身评论

无视觉 API 费用，本地 CPU 运行。

### 三段式图片回复
收到图片立刻发出第一段：
> *"omg wait let me see"*

图片分析完成后发出第二段：
> *"wait ur literally on a boat?? the water is so blue"*

自然跟进第三段：
> *"ok but where even is this, it's gorgeous"*

和真人收到照片时的反应节奏完全一样。

### 主动互动机制
- **新配对打招呼** —— 破冰 / 悬念 / 钩子三种风格轮换
- **超时催回** —— 用户不活跃超过设定时间，主动发「heyyy u still there」
- **图片跟进** —— 发完图后自动追问"怎么样"
- **断点修复** —— 检测到用户连发多条未被认真回应，优先处理

### 行为完全可调
所有性格规则 —— 说话风格、撩骚尺度、语言规则、角色一致性 —— 全在 `agent/prompt_rules.py` 一个文件里。改一个文件，全平台行为同步更新，不需要动引擎代码。

### 无状态 API 设计
Laravel（或任何后端）每次发消息时调用 Agent，把聊天记录从自己数据库传进来。Agent 生成下一条回复后返回。你持有所有数据，Agent 不持久化任何内容。

---

## 能产生什么价值

**对平台**
- 上线第一天就有完整的社交生态，而不是一个空 APP
- 冷启动期有高质量对话的真实用户，留存率提升 3-5 倍
- 每个虚拟用户像真实的人，不会让用户觉得在和机器人聊天

**对团队**
- 每条消息一次 HTTP 调用，JSON 输入，JSON 输出，无状态管理
- 性格行为是一个文件，产品可以自己调，不依赖工程师
- 图片识别本地运行，零视觉 API 费用
- 文字生成使用 DeepSeek，约 $0.001 / 对话轮次

**对产品**
- 任意规模的冷启动都可信
- 有情感深度的对话带动用户回访
- 为高级功能打基础：AI 伴侣、虚拟约会、语音等

---

## 快速开始

**环境要求：** Python 3.11+，4GB 内存（图片识别推荐 8GB）

```bash
# 1. 克隆
git clone https://github.com/yourname/virtual-agent.git
cd virtual-agent

# 2. 安装核心依赖
pip install openai requests pytz python-dotenv fastapi uvicorn mem0ai chromadb

# 3. 安装图片识别（可选，首次下载约 800MB）
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install transformers==4.40.2 timm einops Pillow

# 4. 配置
cp .env.example .env
# 编辑 .env，填写 DEEPSEEK_API_KEY 和 API_BASE_URL

# 5a. 本地调试模式（控制台）
python main.py

# 5b. 生产模式（HTTP API 服务）
python -m uvicorn api:app --host 0.0.0.0 --port 8001

# 6. 验证
curl http://localhost:8001/health
# → {"status": "ok"}
```

---

## 接口说明

### POST `/agent/respond`
每次真实用户发消息时调用。

```json
{
  "virtual_user_id": "36177",
  "real_user_id":    "7830",
  "message":         "hey whats up",
  "message_type":    "text",
  "timezone":        "America/New_York",
  "history": [
    {"role": "user",      "content": "i work as a nurse in Austin"},
    {"role": "assistant", "content": "omg a nurse!! thats so cool"}
  ]
}
```

从数据库传最近 10-20 条消息作为 `history`，Agent 以此作为本次对话的上下文记忆。

**返回：**
```json
{
  "status": true,
  "messages": [
    {"text": "omg hey!!",               "send_image": false, "image_url": null, "delay_seconds": 0},
    {"text": "what took u so long lol", "send_image": false, "image_url": null, "delay_seconds": 2}
  ]
}
```

按顺序推送每条消息，遵守 `delay_seconds` 模拟打字间隔。

**用户发图片：**
```json
{"message": "https://cdn.example.com/photo.jpg", "message_type": "image"}
```

**虚拟用户发图片时**（`send_image: true`）：
```json
{"text": "ok fine here", "send_image": true, "image_url": "https://cdn.example.com/photo.jpg", "delay_seconds": 1}
```
将 `image_url` 作为图片消息推送给用户。

---

### POST `/agent/greet`
新配对成功时调用，触发虚拟用户发第一条消息。

```json
{"virtual_user_id": "36177", "real_user_id": "7830", "timezone": "America/New_York"}
```

---

### POST `/agent/timeout_check`
每 5 分钟对活跃会话调用一次，用户不活跃超过设定时间时返回催回复消息。

```json
{"virtual_user_id": "36177", "real_user_id": "7830"}
```

---

### GET `/agent/debug`
查看当前会话状态（情绪、记忆、角色信息），排查问题用。

```
GET /agent/debug?virtual_user_id=36177&real_user_id=7830
```

---

### GET `/health`
```
GET /health  →  {"status": "ok", "timestamp": 1234567890}
```

---

## 自定义行为

只需编辑 `agent/prompt_rules.py`，这是调整行为唯一需要改的文件：

```python
def get_texting_style_rule():
    return (
        "write exactly like a real american woman casually texting. "
        "mostly lowercase. no apostrophes — write im, dont, cant..."
    )

def get_flirting_rule():
    return (
        "if they flirt, match their energy and push further. "
        "be bold, teasing, keep them wanting more..."
    )

def get_language_rule():
    return "you only speak English. other languages get a confused reply."
```

---

## 初始化特征库

发消息前，虚拟用户需要先有性格特征数据：

```bash
# 单个用户
python trait_generator.py 36177

# 批量处理所有虚拟用户
python trait_generator.py --batch
```

---

## 文件结构

```
virtual_agent/
├── main.py                   # 本地调试控制台
├── api.py                    # 生产 HTTP 服务
├── config.py                 # 所有配置 ← 在这里改
├── trait_generator.py        # 初始化性格特征
│
├── agent/
│   ├── engine.py             # 核心回复逻辑
│   ├── prompt_rules.py       # 行为规则 ← 在这里调
│   └── scheduler.py          # 主动互动调度
│
├── persona/compiler.py       # 特征 → 提示词
├── storage/api_store.py      # 从你的 API 读取用户数据
├── emotion/engine.py         # PAD 情绪引擎
├── memory/manager.py         # 短期 + 长期记忆
├── input/normalizer.py       # 文字 / 图片 / 表情处理
└── input/image_analyzer.py   # Florence-2 视觉模型
```

---

## License

MIT
