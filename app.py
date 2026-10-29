"""NeuraDesk: a dark-themed desktop chat and text-processing assistant."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

from assistant_core import AssistantCore
from database import ChatDatabase
from text_tools import analyze_text, summarize_text, clean_text


BG = "#11131a"
PANEL = "#191c26"
PANEL_2 = "#202432"
TEXT = "#edf0f7"
MUTED = "#a6aec3"
ACCENT = "#8b7cff"
ACCENT_HOVER = "#a095ff"
GREEN = "#6bd6a7"
BORDER = "#303649"


class NeuraDeskApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("NeuraDesk — دستیار هوشمند")
        self.root.geometry("1080x720")
        self.root.minsize(800, 560)
        self.root.configure(bg=BG)

        self.db = ChatDatabase()
        self.core = AssistantCore()
        self.session_id = self.db.create_session("گفت‌وگوی جدید")
        self.busy = False

        self._configure_styles()
        self._build_ui()
        self._append_message("NeuraDesk", "سلام! من NeuraDesk هستم. می‌تونم باهات گفت‌وگو کنم، متن رو خلاصه یا تحلیل کنم و گفتگوها رو ذخیره کنم.\n\nبرای شروع پیام بنویس یا از ابزارهای سمت راست استفاده کن.", "assistant")
        self._refresh_sessions()
        self._set_status("آماده‌ام")

    def _configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", fieldbackground=PANEL_2, background=PANEL_2, foreground=TEXT)
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT, rowheight=28, borderwidth=0)
        style.configure("Treeview.Heading", background=PANEL_2, foreground=TEXT, relief="flat")
        style.map("Treeview", background=[("selected", "#39345e")])

    def _build_ui(self):
        header = tk.Frame(self.root, bg=BG, padx=18, pady=14)
        header.pack(fill="x")
        tk.Label(header, text="NeuraDesk", bg=BG, fg=TEXT, font=("Segoe UI", 19, "bold")).pack(side="left")
        tk.Label(header, text="دستیار چت و پردازش متن", bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(side="left", padx=12)
        self.status = tk.Label(header, text="", bg=BG, fg=GREEN, font=("Segoe UI", 9))
        self.status.pack(side="right")
        self._button(header, "تنظیم هوش مصنوعی آنلاین", self.open_ai_settings, fill=False, secondary=True).pack(side="right", padx=10)

        body = tk.Frame(self.root, bg=BG, padx=14, pady=0)
        body.pack(fill="both", expand=True)

        sidebar = tk.Frame(body, bg=PANEL, width=245, padx=12, pady=12)
        sidebar.pack(side="left", fill="y", padx=(0, 12))
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="گفت‌وگوها", bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))
        self.sessions = tk.Listbox(sidebar, bg=PANEL_2, fg=TEXT, selectbackground="#39345e", selectforeground=TEXT,
                                   relief="flat", borderwidth=0, highlightthickness=0, activestyle="none",
                                   font=("Segoe UI", 10))
        self.sessions.pack(fill="both", expand=True)
        self.sessions.bind("<<ListboxSelect>>", self._on_session_select)
        self._button(sidebar, "＋ گفت‌وگوی جدید", self.new_session, fill=True).pack(fill="x", pady=(10, 5))
        self._button(sidebar, "خروجی گرفتن از گفتگو", self.export_chat, fill=True, secondary=True).pack(fill="x")

        main = tk.Frame(body, bg=PANEL, padx=14, pady=14)
        main.pack(side="left", fill="both", expand=True)
        tk.Label(main, text="گفت‌وگو", bg=PANEL, fg=TEXT, font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.chat = tk.Text(main, bg=BG, fg=TEXT, insertbackground=TEXT, wrap="word", relief="flat",
                            padx=14, pady=12, font=("Segoe UI", 10), state="disabled", spacing1=3, spacing3=8)
        self.chat.pack(fill="both", expand=True, pady=(10, 12))
        self.chat.tag_configure("assistant_name", foreground=ACCENT, font=("Segoe UI", 10, "bold"))
        self.chat.tag_configure("user_name", foreground=GREEN, font=("Segoe UI", 10, "bold"))
        self.chat.tag_configure("body", foreground=TEXT)
        self.chat.tag_configure("time", foreground=MUTED, font=("Segoe UI", 8))

        compose = tk.Frame(main, bg=PANEL)
        compose.pack(fill="x")
        self.input = tk.Text(compose, height=3, bg=PANEL_2, fg=TEXT, insertbackground=TEXT, wrap="word",
                             relief="flat", padx=10, pady=9, font=("Segoe UI", 10), undo=True)
        self.input.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.input.bind("<Control-Return>", lambda _e: self.send_message())
        self._button(compose, "ارسال  ➤", self.send_message, fill=False).pack(side="right", fill="y")

        tools = tk.Frame(body, bg=PANEL, width=220, padx=12, pady=12)
        tools.pack(side="right", fill="y", padx=(12, 0))
        tools.pack_propagate(False)
        tk.Label(tools, text="ابزارهای متن", bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))
        tk.Label(tools, text="متن رو در کادر زیر وارد کن:", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        self.text_box = tk.Text(tools, height=10, bg=PANEL_2, fg=TEXT, insertbackground=TEXT, wrap="word",
                                relief="flat", padx=8, pady=8, font=("Segoe UI", 9))
        self.text_box.pack(fill="x", pady=(6, 10))
        self._button(tools, "خلاصه‌سازی", self.do_summarize, fill=True).pack(fill="x", pady=3)
        self._button(tools, "تحلیل متن", self.do_analyze, fill=True).pack(fill="x", pady=3)
        self._button(tools, "پاک‌سازی فاصله‌ها", self.do_clean, fill=True, secondary=True).pack(fill="x", pady=3)
        self._button(tools, "فرستادن متن به چت", self.send_tool_text, fill=True, secondary=True).pack(fill="x", pady=3)
        tk.Label(tools, text="پردازش متن به‌صورت محلی انجام می‌شود؛ برای مدل زبانی آنلاین، README را ببین.", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 8), wraplength=190, justify="left").pack(anchor="w", pady=(16, 0))

    def _button(self, parent, label, command, fill=False, secondary=False):
        color = PANEL_2 if secondary else ACCENT
        hover = "#30364a" if secondary else ACCENT_HOVER
        button = tk.Button(parent, text=label, command=command, bg=color, fg=TEXT, activebackground=hover,
                           activeforeground=TEXT, relief="flat", bd=0, cursor="hand2",
                           padx=12, pady=9, font=("Segoe UI", 9, "bold"))
        button.bind("<Enter>", lambda _e: button.configure(bg=hover))
        button.bind("<Leave>", lambda _e: button.configure(bg=color))
        return button

    def _set_status(self, text):
        self.status.configure(text=text)

    def _append_message(self, name, content, role):
        self.chat.configure(state="normal")
        tag = "user_name" if role == "user" else "assistant_name"
        self.chat.insert("end", f"{name}  ", tag)
        self.chat.insert("end", datetime.now().strftime("%H:%M") + "\n", "time")
        self.chat.insert("end", content.strip() + "\n\n", "body")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def _persist_and_show(self, role, content):
        self.db.add_message(self.session_id, role, content)
        self._append_message("شما" if role == "user" else "NeuraDesk", content, role)

    def send_message(self):
        if self.busy:
            return
        message = self.input.get("1.0", "end").strip()
        if not message:
            return
        self.input.delete("1.0", "end")
        self._persist_and_show("user", message)
        self.busy = True
        self._set_status("در حال پردازش…")
        try:
            history = [(role, content) for role, content, _created in self.db.get_messages(self.session_id)[:-1]]
            answer = self.core.reply(message, history=history)
            self._persist_and_show("assistant", answer)
            self._set_status("آماده‌ام")
        except Exception as exc:
            self._persist_and_show("assistant", f"در پردازش پیام مشکلی پیش اومد: {exc}")
            self._set_status("خطا در پردازش")
        finally:
            self.busy = False

    def do_summarize(self):
        text = self.text_box.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("خلاصه‌سازی", "اول متنی در کادر ابزارها وارد کن.")
            return
        result = summarize_text(text)
        self._persist_and_show("user", "لطفاً این متن رو خلاصه کن:\n" + text)
        self._persist_and_show("assistant", "خلاصه متن:\n" + result)

    def do_analyze(self):
        text = self.text_box.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("تحلیل متن", "اول متنی در کادر ابزارها وارد کن.")
            return
        result = analyze_text(text)
        formatted = (
            f"تعداد نویسه‌ها: {result['characters']}\n"
            f"تعداد واژه‌ها: {result['words']}\n"
            f"تعداد جمله‌ها: {result['sentences']}\n"
            f"زمان تقریبی خواندن: {result['reading_minutes']} دقیقه\n"
            f"واژه‌های پرتکرار: {', '.join(result['keywords']) or 'موردی پیدا نشد'}"
        )
        self._persist_and_show("user", "این متن رو تحلیل کن:\n" + text)
        self._persist_and_show("assistant", formatted)

    def do_clean(self):
        original = self.text_box.get("1.0", "end").strip()
        if not original:
            messagebox.showinfo("پاک‌سازی", "اول متنی در کادر ابزارها وارد کن.")
            return
        cleaned = clean_text(original)
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", cleaned)
        self._set_status("متن پاک‌سازی شد")

    def send_tool_text(self):
        text = self.text_box.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("ارسال متن", "اول متنی در کادر ابزارها وارد کن.")
            return
        # Send immediately instead of only copying text into the chat input.
        self.input.delete("1.0", "end")
        self.input.insert("1.0", text)
        self.send_message()

    def open_ai_settings(self):
        window = tk.Toplevel(self.root)
        window.title("تنظیم هوش مصنوعی آنلاین")
        window.configure(bg=BG)
        window.resizable(False, False)
        window.transient(self.root)
        window.grab_set()
        panel = tk.Frame(window, bg=PANEL, padx=18, pady=18)
        panel.pack(fill="both", expand=True)
        tk.Label(panel, text="اتصال به مدل زبانی آنلاین", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))
        tk.Label(panel, text="برای پاسخ‌های آزاد و هوشمند، کلید API لازم است. کلید فقط تا بسته‌شدن برنامه در حافظه می‌ماند.",
                 bg=PANEL, fg=MUTED, wraplength=430, justify="left").pack(anchor="w", pady=(0, 12))

        def field(label, initial, show=None):
            tk.Label(panel, text=label, bg=PANEL, fg=TEXT).pack(anchor="w", pady=(5, 3))
            entry = tk.Entry(panel, bg=PANEL_2, fg=TEXT, insertbackground=TEXT, relief="flat",
                             width=58, show=show)
            entry.pack(fill="x", ipady=7)
            entry.insert(0, initial)
            return entry

        key_entry = field("کلید API", self.core.api_key, show="•")
        base_entry = field("آدرس پایه API سازگار با OpenAI", self.core.api_base)
        model_entry = field("نام مدل", self.core.model)
        tk.Label(panel, text="نمونه آدرس: https://api.openai.com/v1 — استفاده از API ممکن است هزینه داشته باشد.",
                 bg=PANEL, fg=MUTED, wraplength=430, justify="left").pack(anchor="w", pady=10)

        def save():
            key = key_entry.get().strip()
            base = base_entry.get().strip().rstrip("/")
            model = model_entry.get().strip()
            if key and (not base.startswith("https://") and not base.startswith("http://")):
                messagebox.showerror("آدرس نامعتبر", "آدرس API باید با https:// یا http:// شروع شود.", parent=window)
                return
            if key and not model:
                messagebox.showerror("مدل نامعتبر", "نام مدل را وارد کن.", parent=window)
                return
            self.core.api_key = key
            self.core.api_base = base or "https://api.openai.com/v1"
            self.core.model = model or "gpt-4o-mini"
            self._set_status("هوش مصنوعی آنلاین فعال است" if key else "حالت محلی")
            window.destroy()
            messagebox.showinfo("تنظیمات", "تنظیمات در حافظه برنامه اعمال شد." if key else "کلید پاک شد؛ برنامه در حالت محلی است.")

        self._button(panel, "ذخیره تنظیمات", save, fill=True).pack(anchor="e", pady=(8, 0))

    def new_session(self):
        self.session_id = self.db.create_session("گفت‌وگوی جدید")
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")
        self._append_message("NeuraDesk", "گفت‌وگوی جدید آماده است. چه کاری انجام بدیم؟", "assistant")
        self._refresh_sessions()

    def _refresh_sessions(self):
        self.sessions.delete(0, "end")
        self.session_ids = []
        for session_id, title, _created in self.db.list_sessions():
            self.session_ids.append(session_id)
            self.sessions.insert("end", title)
        if self.session_id in self.session_ids:
            index = self.session_ids.index(self.session_id)
            self.sessions.selection_clear(0, "end")
            self.sessions.selection_set(index)

    def _on_session_select(self, _event=None):
        selected = self.sessions.curselection()
        if not selected:
            return
        new_id = self.session_ids[selected[0]]
        if new_id == self.session_id:
            return
        self.session_id = new_id
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        for role, content, created in self.db.get_messages(self.session_id):
            name = "شما" if role == "user" else "NeuraDesk"
            tag = "user_name" if role == "user" else "assistant_name"
            self.chat.insert("end", f"{name}  ", tag)
            self.chat.insert("end", created[11:16] if len(created) >= 16 else "", "time")
            self.chat.insert("end", "\n" + content + "\n\n", "body")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def export_chat(self):
        messages = self.db.get_messages(self.session_id)
        if not messages:
            messagebox.showinfo("خروجی", "این گفتگو پیامی ندارد.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text file", "*.txt")],
                                            initialfile="neuradesk-chat.txt")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                for role, content, created in messages:
                    label = "شما" if role == "user" else "NeuraDesk"
                    handle.write(f"[{created}] {label}\n{content}\n\n")
            messagebox.showinfo("خروجی", "گفتگو با موفقیت ذخیره شد.")
        except OSError as exc:
            messagebox.showerror("خطا", f"ذخیره فایل انجام نشد:\n{exc}")

    def close(self):
        self.db.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = NeuraDeskApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()


if __name__ == "__main__":
    main()
