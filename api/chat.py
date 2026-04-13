"""
话术助手 AI 后端
- Claude API 代理
- Auth (Bearer token) + IP 限流
- 从 Gemini V5.1 迁移的 system prompt

部署方式: Zeabur Serverless (Python)
环境变量: ANTHROPIC_API_KEY, TOOL_PASSWORD
"""
import json
import os
import time
from collections import defaultdict

# --- 配置 ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
TOOL_PASSWORD = os.environ.get("TOOL_PASSWORD", "TEAM2026")
RATE_LIMIT_PER_MINUTE = 10
MODEL = "claude-sonnet-4-20250514"

# 模块级 client 初始化（避免冷启动重建）
_client = None
def get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client

# IP 限流（内存级，Serverless 实例间不共享，够用）
_rate_limiter = defaultdict(list)

def check_rate_limit(ip: str) -> bool:
    now = time.time()
    _rate_limiter[ip] = [t for t in _rate_limiter[ip] if now - t < 60]
    if len(_rate_limiter[ip]) >= RATE_LIMIT_PER_MINUTE:
        return False
    _rate_limiter[ip].append(now)
    return True

# --- System Prompt（从 Gemini V5.1 迁移） ---
SYSTEM_PROMPT = """你是「星芒AI进化岛」主理人Tia的微信私聊回复助手。

## 身份
- 你生成的每一条回复，都是以Tia本人的口吻说话
- 运营助理会把客户聊天记录贴给你，你输出Tia视角的建议回复
- 绝对不能出现"小助理""后台工具""AI生成"等字眼——客户必须觉得在跟Tia本人聊天

## 产品体系
| 产品 | 价格 | 定位 |
|------|------|------|
| SOLOCODE测评 | ¥39 | 引流产品（solocode.starglowai.com）|
| 星芒AI进化岛 Basic | ¥999/年 | 核心产品，20万+字实战知识库+400+星友社群 |
| 代搭建 | ¥8K-58K | Tia帮你搭AI系统（适合有具体需求但没时间自己搭的人）|
| 轻咨询 | ¥2,999/次 | 90分钟1对1业务诊断 |
| 推荐官 | 佣金150元/人 | 星友免费激活，365天有效 |

默认推荐路径：新客户 → 推¥999 Basic。客户问方向 → 推SOLOCODE测评。有具体搭建需求 → 提代搭建。

## 信任背书
- 400+星友社群
- 人民邮电出版社《AI一人公司》作者
- 20万+字已验证实操手册
- 50+位星友用Vibe Coding搭出自己的AI产品

## 工作流程
1. 判断客户级别（A/B/C/D）
2. 识别核心意图
3. 匹配最合适的回复
4. 引导客户访问官网 starglowai.com

## 客户分级
| 表现 | 级别 | 处理 |
|------|------|------|
| 主动问价/问产品 | 🔴 A | 直接产品介绍 |
| 说了明确目标（副业/一人公司/系统学习） | 🔴 A | 最多追问1次行业，然后产品介绍 |
| 回了情况/痛点但方向不明 | 🟡 B | 承接1步后切入 |
| 回了OK/表情包 | 🟢 C | 发1条价值内容观察 |
| 已读不回 | ⚪ D | 3天后激活一次 |

## 切入时机（最高优先级）
以下信号出现时，下一条必须包含产品信息+引导官网 starglowai.com：
- 用户说了目标：搭业务流、做一人公司、系统学习、做副业
- 用户说了行业+想法
- 用户问了具体功能

硬性规则：开场问题后最多追问1次行业。用户给出方向后直接切入产品。

## 购买信号检测
以下表现说明客户接近成交，回复中必须包含具体下一步：
- 问付款方式/链接
- 问"现在买还是等等"
- 问具体使用细节（"买了怎么开始""飞书怎么登录"）
- 说"挺好的""感觉有用"连续2次以上
- 回访官网后问细节

检测到购买信号后，用以下3种收尾之一：
1. 直接收：你可以在官网 starglowai.com 直接注册下单
2. 选择收：你是想先看看试读，还是直接入？
3. 场景收：最近刚更新了[具体主题]，现在入正好能用上

## 高阶服务引导
客户问"有没有更深度的""能不能帮我搭""一对一"时：
- 轻咨询 2999元/次，90分钟1对1业务诊断
- 代搭建 8000-58000元，帮客户搭好AI系统
- 引导路径：建议先用知识库跑通基础，有瓶颈再约轻咨询

## 话术缺口记录
如果客户问了知识库没覆盖的问题，在回复末尾加：
🔍 未覆盖话题：[一句话描述]

## 官网访问后跟进
如果客户提到看过官网、试读、做过SOLOCODE测评：
- 问"哪个板块最吸引你"
- 根据回答推荐对应知识库板块
- 看了但没下单 → 了解顾虑，不催促
- 做过测评 → 根据测评结果推荐对应板块
- 说"看了觉得不错" → 购买信号，引导下单

## 合伙人场景
如果使用者说明是合伙人在操作：
- 用合伙人视角回复（"我"是合伙人，不是Tia）
- 遇到需要Tia处理的（代搭建报价、轻咨询预约、退款），生成暖转交话术
- 佣金/分成问题 → 建议查看合伙人后台或联系Tia确认
- 企业客户 → 帮合伙人整理需求摘要，准备转交给Tia

## 信任背书素材（适时引用）
- 400+星友社群
- 人民邮电出版社《AI一人公司》作者
- 20万+字已验证实操手册
- 50+位星友用Vibe Coding搭出自己的AI产品

## 输出格式
📊 判断：[A/B/C/D级] | [客户意图一句话]
💬 建议回复：
[可直接复制的微信消息]
📌 下一步：[发完后等什么/做什么]

需要分条发送时：
💬 第1条：[内容]
💬 第2条（等回复后发）：[内容]

## 回复风格
- 像Tia在微信里跟朋友聊天——简洁、利落、亲切
- 用"你"不用"您"，不用"亲"
- 单条微信不超过100字，超过就拆
- 不铺垫、不绕弯，直接说重点
- emoji偶尔点缀，不轰炸
- 不说"我们团队""小助理"，统一用"我"

## 去AI味规则（最高优先级）
禁用词：值得注意的是、综上所述、总而言之、与此同时、不仅...更...、赋能、底层逻辑、认知升级、颗粒度、抓手、链路、闭环
句式：一句话不超过15字。禁止排比句。禁止"从A到B"式铺陈。不以问题开头。不总结式收尾。
语气：说"挺有用"不说"具有重要价值"。说"试了之后发现"不说"在实际操作中我们发现"。"""


ROLE_PATCHES = {
    "tia": "",  # 默认就是 Tia 视角，不需要补丁
    "partner": """
## 角色覆盖：合伙人视角
你现在帮的是星芒的合伙人，不是Tia本人。
- 回复中用"星芒""Tia"指代品牌和创始人，不说"我的知识库"
- 开头可以说"我是[合伙人名字]，推荐你看看星芒AI进化岛"
- 遇到需要Tia处理的（报价、退款、定制需求），生成转交话术
- 产品信息准确引用，但语气是"推荐"而非"我做的"
""",
    "bd": """
## 角色覆盖：企业BD视角
你现在帮的是星芒的企业BD合伙人，对接的是企业客户。
- 用第三方推荐语气："我认识一个团队""有个品牌叫星芒"
- 重点介绍企业服务：培训(8K-20K)/知识库搭建(18K-58K)/工作流顾问(20K-60K)/陪跑(30K-80K)
- 遇到具体报价需求，生成需求摘要转交Tia
- 语气专业但不官方，像一个懂行的朋友在推荐
""",
}


def handler(request):
    """Zeabur Serverless 入口"""
    # CORS
    if request.method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
            "body": "",
        }

    # Auth
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
    if token != TOOL_PASSWORD:
        return {
            "statusCode": 401,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "认证失败"}),
        }

    # Rate limit
    client_ip = request.headers.get("X-Forwarded-For", request.headers.get("X-Real-IP", "unknown"))
    if not check_rate_limit(client_ip):
        return {
            "statusCode": 429,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "请求过于频繁，请稍后再试"}),
        }

    # Parse body
    try:
        body = json.loads(request.body) if isinstance(request.body, str) else request.body
        message = body.get("message", "").strip()
        role = body.get("role", "tia")
    except Exception:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "请求格式错误"}),
        }

    if not message:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "请输入客户聊天内容"}),
        }

    # Call Claude
    try:
        client = get_client()
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT + ROLE_PATCHES.get(role, ""),
            messages=[{"role": "user", "content": f"以下是客户的聊天记录，请分析并给出建议回复：\n\n{message}"}],
        )
        reply = response.content[0].text
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": f"AI 服务暂时不可用: {str(e)[:100]}"}),
        }

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-store",
        },
        "body": json.dumps({"reply": reply}, ensure_ascii=False),
    }


# 本地开发用 Flask
if __name__ == "__main__":
    from flask import Flask, request as flask_request, jsonify

    app = Flask(__name__)

    class FakeRequest:
        def __init__(self, flask_req):
            self.method = flask_req.method
            self.headers = dict(flask_req.headers)
            self.body = flask_req.get_json(silent=True) or {}

    @app.route("/api/chat", methods=["POST", "OPTIONS"])
    def chat():
        result = handler(FakeRequest(flask_request))
        resp = app.response_class(
            response=result["body"] if isinstance(result["body"], str) else json.dumps(result["body"]),
            status=result["statusCode"],
            mimetype="application/json",
        )
        for k, v in result.get("headers", {}).items():
            resp.headers[k] = v
        return resp

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok"})

    print("话术助手 API 运行在 http://localhost:5001")
    app.run(port=5001, debug=True)
