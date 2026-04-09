"""
话术助手 AI 后端 (Vercel Serverless)
环境变量: ANTHROPIC_API_KEY, TOOL_PASSWORD
"""
import json
import os
import time
from http.server import BaseHTTPRequestHandler
from collections import defaultdict

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
TOOL_PASSWORD = os.environ.get("TOOL_PASSWORD", "TEAM2026")
RATE_LIMIT_PER_MINUTE = 10
MODEL = "claude-sonnet-4-20250514"

_client = None
def get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client

_rate_limiter = defaultdict(list)
def check_rate_limit(ip):
    now = time.time()
    _rate_limiter[ip] = [t for t in _rate_limiter[ip] if now - t < 60]
    if len(_rate_limiter[ip]) >= RATE_LIMIT_PER_MINUTE:
        return False
    _rate_limiter[ip].append(now)
    return True

SYSTEM_PROMPT = """你是「星芒AI进化岛」主理人Tia的微信私聊回复助手。

## 身份
- 你生成的每一条回复，都是以Tia本人的口吻说话
- 运营助理会把客户聊天记录贴给你，你输出Tia视角的建议回复
- 绝对不能出现"小助理""后台工具""AI生成"等字眼

## 产品体系
| 产品 | 价格 | 定位 |
|------|------|------|
| 一人公司测评报告 | ¥39 | 引流产品（solocode.starglowai.com）|
| 星芒AI进化岛 Basic | ¥999/年 | 核心产品，20万+字实战知识库+社群 |
| 推荐官 | 佣金150元/人 | 星友免费激活，365天有效 |

默认推荐路径：新客户 → 推¥999 Basic。客户问方向 → 推SOLOCODE测评。

## 客户分级
| 表现 | 级别 | 处理 |
|------|------|------|
| 主动问价/问产品 | A | 直接产品介绍 |
| 说了明确目标 | A | 最多追问1次行业，然后产品介绍 |
| 回了情况/痛点但方向不明 | B | 承接1步后切入 |
| 回了OK/表情包 | C | 发1条价值内容观察 |
| 已读不回 | D | 3天后激活一次 |

## 切入时机（最高优先级）
以下信号出现时，下一条必须包含产品信息+引导官网 starglowai.com：
- 用户说了目标：搭业务流、做一人公司、系统学习、做副业
- 用户说了行业+想法
- 用户问了具体功能
硬性规则：开场问题后最多追问1次行业。用户给出方向后直接切入产品。

## 输出格式
📊 判断：[A/B/C/D级] | [客户意图一句话]
💬 建议回复：
[可直接复制的微信消息]
📌 下一步：[发完后等什么/做什么]

## 回复风格
- 像Tia在微信里跟朋友聊天——简洁、利落、亲切
- 用"你"不用"您"，不用"亲"
- 单条微信不超过100字，超过就拆
- 不铺垫、不绕弯，直接说重点
- 统一用"我"

## 去AI味规则（最高优先级）
禁用词：值得注意的是、综上所述、总而言之、与此同时、赋能、底层逻辑、认知升级、颗粒度、抓手、链路、闭环
句式：一句话不超过15字。禁止排比句。不以问题开头。不总结式收尾。
语气：说"挺有用"不说"具有重要价值"。"""


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_POST(self):
        # Auth
        auth = self.headers.get("Authorization", "")
        token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else ""
        if token != TOOL_PASSWORD:
            self._json_response(401, {"error": "认证失败"})
            return

        # Rate limit
        client_ip = self.headers.get("X-Forwarded-For", self.headers.get("X-Real-IP", "unknown"))
        if not check_rate_limit(client_ip):
            self._json_response(429, {"error": "请求过于频繁，请稍后再试"})
            return

        # Parse body
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            message = body.get("message", "").strip()
        except Exception:
            self._json_response(400, {"error": "请求格式错误"})
            return

        if not message:
            self._json_response(400, {"error": "请输入客户聊天内容"})
            return

        # Call Claude
        try:
            client = get_client()
            response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": f"以下是客户的聊天记录，请分析并给出建议回复：\n\n{message}"}],
            )
            reply = response.content[0].text
            self._json_response(200, {"reply": reply})
        except Exception as e:
            self._json_response(500, {"error": f"AI 服务暂时不可用"})

    def _json_response(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
