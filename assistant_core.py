"""Local rule-based conversational core for NeuraDesk."""
from __future__ import annotations

import ast
import operator
import re
import json
import os
import urllib.request
import urllib.error
from datetime import datetime
from text_tools import analyze_text, summarize_text, clean_text


_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARYOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def safe_calculate(expression: str):
    """Evaluate a basic arithmetic expression without eval()."""
    if len(expression) > 120:
        raise ValueError("عبارت بیش از حد طولانی است.")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError("عبارت ریاضی معتبر نیست.") from exc

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            if abs(node.value) > 10**12:
                raise ValueError("عدد بیش از حد بزرگ است.")
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 8:
                raise ValueError("توان بزرگ مجاز نیست.")
            value = _ALLOWED_BINOPS[type(node.op)](left, right)
            if isinstance(value, (int, float)) and abs(value) > 10**100:
                raise ValueError("نتیجه بیش از حد بزرگ است.")
            return value
        if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
            return _ALLOWED_UNARYOPS[type(node.op)](visit(node.operand))
        raise ValueError("فقط اعداد و عملگرهای +، -، *، /، //، % و توان مجاز هستند.")

    try:
        return visit(tree)
    except ZeroDivisionError as exc:
        raise ValueError("تقسیم بر صفر مجاز نیست.") from exc
    except OverflowError as exc:
        raise ValueError("نتیجه بیش از حد بزرگ است.") from exc


class AssistantCore:
    """Rule-based local assistant, with optional OpenAI-compatible API support."""

    def __init__(self):
        self.api_key = os.getenv("NEURADESK_API_KEY", "").strip()
        self.api_base = os.getenv("NEURADESK_API_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("NEURADESK_MODEL", "gpt-4o-mini").strip()

    def _api_reply(self, message: str, history=None) -> str | None:
        if not self.api_key:
            return None
        endpoint = self.api_base + "/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are NeuraDesk, a helpful, accurate assistant. Reply in the same language as the user. Be clear, useful, and honest if unsure."},
                *([{"role": item[0], "content": item[1]} for item in (history or []) if item[0] in ("user", "assistant")][-12:]),
                {"role": "user", "content": message},
            ],
            "temperature": 0.4,
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                data = json.loads(response.read().decode("utf-8"))
            answer = data["choices"][0]["message"]["content"]
            if isinstance(answer, str) and answer.strip():
                return answer.strip()
            return None
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                detail = str(exc)
            raise RuntimeError(f"خطای سرویس هوش مصنوعی (HTTP {exc.code}): {detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"اتصال به سرویس هوش مصنوعی برقرار نشد: {exc}") from exc
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("پاسخ سرویس هوش مصنوعی قابل‌خواندن نبود؛ آدرس و نام مدل را بررسی کن.") from exc

    def reply(self, message: str, history=None) -> str:
        original = message.strip()
        if not original:
            return "پیامت خالیه؛ یک سؤال یا متن بفرست."
        text = clean_text(original)
        low = text.casefold()

        # Explicit local tools remain local and deterministic. For other prompts,
        # use an optional configured API; if it fails, continue with local behavior.
        local_commands = ("خلاصه کن", "خلاصه‌سازی", "summarize", "تحلیل کن", "تحلیل متن",
                          "analyze text", "حساب کن", "محاسبه کن", "calculate")
        if self.api_key and not any(command in low for command in local_commands):
            online_answer = self._api_reply(text, history=history)
            if online_answer:
                return online_answer

        if any(word in low for word in ("سلام", "درود", "hello", "hi ", "hey")):
            return "سلام! 👋 آماده‌ام کمک کنم. می‌تونی سؤال بپرسی، متن بدی تا خلاصه یا تحلیلش کنم، یا یک محاسبه ساده بخوای."
        if any(word in low for word in ("چه کار", "راهنما", "help", "قابلیت", "چه کاری")):
            return ("من می‌تونم:\n"
                    "• متن رو خلاصه و تحلیل کنم\n"
                    "• فاصله‌های اضافی رو پاک کنم\n"
                    "• تعداد واژه‌ها و واژه‌های پرتکرار رو بگم\n"
                    "• عبارت ریاضی ساده مثل «حساب کن 12*(4+3)» رو حساب کنم\n"
                    "• گفتگوها رو در همین برنامه ذخیره کنم\n\n"
                    "من یک دستیار محلی ساده‌ام و دانش عمومی نامحدود یا مدل زبانی بزرگ ندارم.")
        if any(word in low for word in ("ساعت", "تاریخ امروز", "امروز چندمه", "time now")):
            return "تاریخ و زمان سیستم: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if any(token in low for token in ("خلاصه کن", "خلاصه‌سازی", "summarize")):
            candidate = re.sub(r"^(لطفاً\s*)?(این متن رو|متن زیر رو)?\s*(خلاصه کن|خلاصه‌سازی کن|summarize)\s*[:：]?\s*", "", text, flags=re.I)
            candidate = candidate.strip() or text
            return "خلاصه متن:\n" + summarize_text(candidate)
        if any(token in low for token in ("تحلیل کن", "تحلیل متن", "analyze text")):
            result = analyze_text(text)
            return (f"تحلیل متن:\n• نویسه‌ها: {result['characters']}\n• واژه‌ها: {result['words']}\n"
                    f"• جمله‌ها: {result['sentences']}\n• زمان مطالعه: حدود {result['reading_minutes']} دقیقه\n"
                    f"• واژه‌های پرتکرار: {', '.join(result['keywords']) or 'پیدا نشد'}")
        calc_match = re.match(r"^(?:حساب کن|محاسبه کن|calculate)\s*[:：]?\s*(.+)$", text, flags=re.I)
        if calc_match:
            try:
                value = safe_calculate(calc_match.group(1))
                return f"نتیجه: {value:g}" if isinstance(value, float) else f"نتیجه: {value}"
            except ValueError as exc:
                return f"نتونستم محاسبه کنم: {exc}"
        if len(text) > 350:
            result = analyze_text(text)
            return (f"متن نسبتاً بلندی فرستادی ({result['words']} واژه). می‌تونم خلاصه‌اش کنم یا تحلیلش کنم.\n"
                    "برای خلاصه‌سازی، اول پیام بنویس «خلاصه کن:» و بعد متن رو قرار بده.")
        return ("متوجه پیامتم، اما در حالت محلی هنوز به یک مدل زبانی بزرگ وصل نیستم؛ پس نمی‌خوام جواب ساختگی بدم.\n\n"
                "می‌تونی از من بخوای «راهنما»، «تحلیل کن: متن»، «خلاصه کن: متن» یا «حساب کن: 12*(4+3)».\n"
                "برای پاسخ‌های آزادتر می‌شه در نسخه بعدی یک API مدل زبانی به برنامه اضافه کرد.")
