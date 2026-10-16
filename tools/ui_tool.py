#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
界面工具 —— 改配色、改文字，全程不用看代码。

用法：双击「改界面.command」，或运行 python3 tools/ui_tool.py
"""

import os
import re
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, ttk

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_FILE = os.path.join(BASE, "web", "index.html")

BG = "#1c1a18"
CARD = "#232120"
CARD_ON = "#2a2724"
FG = "#f0ebe3"
FG2 = "#8a8177"

# ══════════════════════════════════════════════════════════
#  配色方案
# ══════════════════════════════════════════════════════════

SCHEMES = [
    dict(name="经典金", desc="现在用的",
         bg="#0e0c0a", surface="#1a1815", surface2="#211f1b", surface3="#2b2823",
         text="#f0ebe3", text2="#948a7d", text3="#5e5750",
         accent="#d4a574", accent_rgb="212,165,116",
         success="#8fbf7a", warn="#e0a458"),
    dict(name="深海蓝", desc="冷静专业",
         bg="#0a0f1a", surface="#141a26", surface2="#1b2231", surface3="#243044",
         text="#eef3fa", text2="#8a97a8", text3="#5a6577",
         accent="#4a90d9", accent_rgb="74,144,217",
         success="#5cc98a", warn="#e8a33d"),
    dict(name="薄荷绿", desc="清爽自然",
         bg="#0a1210", surface="#131f1c", surface2="#1a2925", surface3="#233833",
         text="#eaf5f2", text2="#87a099", text3="#566e67",
         accent="#4fb8a5", accent_rgb="79,184,165",
         success="#7dd87d", warn="#e0b050"),
    dict(name="珊瑚橙", desc="温暖活泼",
         bg="#120c0a", surface="#1f1614", surface2="#2a1e1b", surface3="#382824",
         text="#f7ece8", text2="#a89189", text3="#715f58",
         accent="#e07a5f", accent_rgb="224,122,95",
         success="#9ccf7a", warn="#e8b04a"),
    dict(name="紫罗兰", desc="优雅神秘",
         bg="#0e0a14", surface="#181323", surface2="#211a2f", surface3="#2d2440",
         text="#f1ecfa", text2="#9c92b0", text3="#665e7a",
         accent="#9d7cd8", accent_rgb="157,124,216",
         success="#7fd4a8", warn="#e8a95c"),
    dict(name="玫瑰粉", desc="柔和温暖",
         bg="#120a0e", surface="#1f1319", surface2="#2a1a22", surface3="#38242e",
         text="#faeef2", text2="#ab8b96", text3="#745e66",
         accent="#d96a8a", accent_rgb="217,106,138",
         success="#8fd4a0", warn="#e8a860"),
    dict(name="石墨黑", desc="极简冷静",
         bg="#0a0a0a", surface="#161616", surface2="#1f1f1f", surface3="#2b2b2b",
         text="#f0f0f0", text2="#909090", text3="#5e5e5e",
         accent="#a0a0a0", accent_rgb="160,160,160",
         success="#7fc87f", warn="#dcb050"),
    dict(name="琥珀", desc="复古乐器感",
         bg="#0f0b06", surface="#1c1610", surface2="#261e15", surface3="#34291d",
         text="#f5efe5", text2="#a39583", text3="#6d6252",
         accent="#e0a03c", accent_rgb="224,160,60",
         success="#96c46a", warn="#e8c04a"),
]

# ══════════════════════════════════════════════════════════
#  可改的文字
# ══════════════════════════════════════════════════════════

TEXT_ITEMS = [
    dict(key="title",  group="名称", label="网页标题",
         pattern=r"<title>(.*?)</title>",
         hint="浏览器标签页上显示的"),
    dict(key="brand_cn", group="名称", label="品牌中文名",
         pattern=r'<div class="brand-cn">(.*?)</div>',
         hint="界面左上角的大字"),
    dict(key="brand_en", group="名称", label="品牌英文名",
         pattern=r'<div class="brand-en">(.*?)</div>',
         hint="中文名下面那行小字"),

    dict(key="mode_guitar", group="乐器按钮", label="第一个按钮",
         pattern=r'data-mode="guitar">(.*?)</button>', hint=""),
    dict(key="mode_ukulele", group="乐器按钮", label="第二个按钮",
         pattern=r'data-mode="ukulele">(.*?)</button>', hint=""),
    dict(key="mode_piano", group="乐器按钮", label="第三个按钮",
         pattern=r'data-mode="piano">(.*?)</button>', hint=""),

    dict(key="view_needle", group="视图按钮", label="指针视图",
         pattern=r'data-view="needle">(.*?)</button>', hint=""),
    dict(key="view_strobe", group="视图按钮", label="频闪视图",
         pattern=r'data-view="strobe">(.*?)</button>', hint=""),

    dict(key="start_btn", group="其他按钮", label="开始按钮",
         pattern=r'id="startBtn"[^>]*>(.*?)</button>',
         hint="页面下方的大按钮"),

    dict(key="label_a4", group="设置项文字", label="标准音高",
         pattern=r'<span class="setting-label">标准音高</span>', hint=""),
    dict(key="label_view", group="设置项文字", label="视图",
         pattern=r'<span class="setting-label">视图</span>', hint=""),
    dict(key="label_app", group="设置项文字", label="手机 App",
         pattern=r'<span class="setting-label">手机 App</span>', hint=""),
]


# ══════════════════════════════════════════════════════════
#  文件读写
# ══════════════════════════════════════════════════════════

def read_file():
    with open(WEB_FILE, encoding="utf-8") as f:
        return f.read()


def write_file(text):
    shutil.copy2(WEB_FILE, WEB_FILE + ".bak")
    try:
        with open(WEB_FILE, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        shutil.copy2(WEB_FILE + ".bak", WEB_FILE)
        raise
    finally:
        if os.path.isfile(WEB_FILE + ".bak"):
            os.remove(WEB_FILE + ".bak")


def hex_to_rgb(h):
    """'#d4a574' → (212, 165, 116)"""
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return (212, 165, 116)


def rgb_str(hexcolor):
    """'#d4a574' → '212,165,116'（给 rgba() 用）"""
    return ",".join(str(x) for x in hex_to_rgb(hexcolor))


def lighten(hexcolor, amount=0.28):
    """把颜色调亮，用作渐变的高光端。

    主按钮的渐变是「浅色 → 主色」，浅色由主色推导，
    这样换配色时按钮也跟着变。
    """
    r, g, b = hex_to_rgb(hexcolor)
    r = int(r + (255 - r) * amount)
    g = int(g + (255 - g) * amount)
    b = int(b + (255 - b) * amount)
    return f"#{r:02x}{g:02x}{b:02x}"


def sync_offline():
    """同步 App 内置的离线版。"""
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(BASE, "tools", "build_web.py"), "--from-web"],
            capture_output=True, text=True, timeout=60, cwd=BASE,
        )
        return r.returncode == 0
    except Exception:
        return False


def read_scheme():
    """读出当前配色。"""
    text = read_file()
    out = {}
    m = re.search(r":root\{(.*?)\}", text, re.S)
    if not m:
        return out
    block = m.group(1)
    for key, var in [("bg", "--bg"), ("surface", "--surface"),
                     ("text", "--text"), ("accent", "--accent")]:
        mm = re.search(rf"{re.escape(var)}\s*:\s*([^;]+);", block)
        if mm:
            out[key] = mm.group(1).strip()
    return out


def read_texts():
    """读出所有可改文字的当前值。"""
    text = read_file()
    out = {}
    for item in TEXT_ITEMS:
        m = re.search(item["pattern"], text, re.S | re.I)
        if m:
            if m.groups():
                out[item["key"]] = m.group(1).strip()
            else:
                mm = re.search(r">([^<>]+)</span>", m.group(0))
                out[item["key"]] = mm.group(1).strip() if mm else ""
    return out


def apply_scheme(scheme):
    text = read_file()
    m = re.search(r":root\{.*?\}", text, re.S)
    if not m:
        return False, "找不到配色区块，文件可能被改坏了"

    # 推导辅助色彩。
    # 页面上除了主色，还需要：
    #   · 浅色版（主按钮渐变的高光端）
    #   · RGB 分量（rgba() 和 canvas 绘制要用）
    # 不手工维护这些，全部从主色算出来，避免不一致。
    accent = scheme["accent"]
    accent_light = lighten(accent)
    accent_rgb = scheme.get("accent_rgb") or rgb_str(accent)

    success = scheme.get("success", "#8fbf7a")
    warn = scheme.get("warn", "#e0a458")

    new_block = f""":root{{
    --bg:{scheme['bg']};
    --surface:{scheme['surface']};
    --surface-2:{scheme['surface2']};
    --surface-3:{scheme['surface3']};
    --border:rgba(240,235,227,.06);
    --border-2:rgba(240,235,227,.10);
    --text:{scheme['text']};
    --text-2:{scheme['text2']};
    --text-3:{scheme['text3']};

    /* 主题色（由 tools/ui_tool.py 生成）*/
    --accent:{accent};
    --accent-light:{accent_light};
    --accent-soft:rgba({accent_rgb},.13);
    --accent-rgb:{accent_rgb};
    --accent-light-rgb:{rgb_str(accent_light)};

    --success:{success};
    --success-rgb:{rgb_str(success)};
    --warn:{warn};
    --warn-rgb:{rgb_str(warn)};
  }}"""

    text = text[:m.start()] + new_block + text[m.end():]

    # 同步 theme() 函数里的兜底值。
    # 那个函数是给 canvas 读主题色用的，它的 fallback 也应该是当前配色，
    # 否则万一 CSS 变量读不到，画布会回到旧颜色。
    for fbs, new_val in [
        ("accentRgb", accent_rgb),
        ("successRgb", rgb_str(success)),
    ]:
        text = re.sub(
            rf"({fbs}:\s*get\('--[\w-]+',\s*')[^']*(')",
            rf"\g<1>{new_val}\g<2>",
            text, count=1,
        )

    for fb_key, var_name, new_val in [
        ("accent", "--accent", accent),
        ("surface2", "--surface-2", scheme['surface2']),
        ("text", "--text", scheme['text']),
    ]:
        text = re.sub(
            rf"({fb_key}:\s*get\('{re.escape(var_name)}',\s*')[^']*(')",
            rf"\g<1>{new_val}\g<2>",
            text, count=1,
        )
    try:
        write_file(text)
    except Exception as e:
        return False, f"写入失败：{e}"

    synced = sync_offline()
    msg = f"配色已换成「{scheme['name']}」"
    msg += "\nApp 离线版也同步了" if synced else "\n（离线版同步失败，发布时会自动处理）"
    return True, msg


def apply_texts(values):
    """把用户改好的文字写进去。"""
    text = read_file()
    changed = []

    for item in TEXT_ITEMS:
        key = item["key"]
        if key not in values:
            continue
        new = values[key].strip()
        if not new:
            continue     # 空的不改

        m = re.search(item["pattern"], text, re.S | re.I)
        if not m:
            continue

        if m.groups():
            old = m.group(1)
            if old.strip() == new:
                continue
            # 只替换匹配到的那一处
            start = m.start(1) - m.start()
            end = m.end(1) - m.start()
            matched = m.group(0)
            replaced = matched[:start] + new + matched[end:]
            text = text[:m.start()] + replaced + text[m.end():]
        else:
            # 整段匹配（设置项标签）
            old_label = re.search(r">([^<>]+)</span>", m.group(0))
            if old_label and old_label.group(1).strip() == new:
                continue
            matched = m.group(0)
            replaced = re.sub(r">([^<>]+)</span>", f">{new}</span>", matched)
            text = text[:m.start()] + replaced + text[m.end():]

        changed.append(f"{item['label']}：{old.strip() if m.groups() else '(原值)'} → {new}")

    if not changed:
        return True, "没有需要改的地方", []

    try:
        write_file(text)
    except Exception as e:
        return False, f"写入失败：{e}", []

    sync_offline()
    return True, f"改了 {len(changed)} 处", changed


# ══════════════════════════════════════════════════════════
#  界面
# ══════════════════════════════════════════════════════════

class App:
    def __init__(self, root):
        self.root = root
        self.selected_scheme = None
        self.text_vars = {}

        root.title("改界面 · 始信音乐调音器")
        root.configure(bg=BG)
        root.geometry("780x680")
        root.minsize(720, 620)

        self.f_title = tkfont.Font(family="PingFang SC", size=16, weight="bold")
        self.f_body = tkfont.Font(family="PingFang SC", size=12)
        self.f_name = tkfont.Font(family="PingFang SC", size=12, weight="bold")
        self.f_desc = tkfont.Font(family="PingFang SC", size=10)
        self.f_hint = tkfont.Font(family="PingFang SC", size=11)
        self.f_small = tkfont.Font(family="PingFang SC", size=10)
        self.f_group = tkfont.Font(family="PingFang SC", size=11, weight="bold")
        self.f_btn = tkfont.Font(family="PingFang SC", size=13, weight="bold")

        self.build()

    # ──────────────────────────────────────────────

    def build(self):
        head = tk.Frame(self.root, bg=BG)
        head.pack(fill="x", padx=26, pady=(18, 4))
        tk.Label(head, text="改界面", font=self.f_title,
                 bg=BG, fg=FG).pack(anchor="w")
        tk.Label(head, text="改完点「保存」，然后双击「预览效果」看真实效果",
                 font=self.f_hint, bg=BG, fg=FG2).pack(anchor="w", pady=(4, 0))

        # ── 标签页 ──
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=CARD, foreground=FG2,
                        padding=[18, 9], font=self.f_body, borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", CARD_ON)],
                  foreground=[("selected", FG)])

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=22, pady=10)

        tab1 = tk.Frame(nb, bg=BG)
        tab2 = tk.Frame(nb, bg=BG)
        nb.add(tab1, text="  配色  ")
        nb.add(tab2, text="  文字  ")

        self.build_colors(tab1)
        self.build_texts(tab2)

        # ── 底部（要在自动高亮之前建好，因为高亮逻辑会碰它）──
        foot = tk.Frame(self.root, bg=BG)
        foot.pack(fill="x", padx=26, pady=(4, 18))

        self.status = tk.Label(foot, text="", font=self.f_hint, bg=BG, fg=FG2)
        self.status.pack(side="left")

        self.save_btn = tk.Button(
            foot, text="保存", font=self.f_btn,
            bg="#3a3630", fg="#6b6358", relief="flat", padx=32, pady=10,
            state="disabled", command=self.do_save,
            activebackground="#4a453d", activeforeground=FG,
            disabledforeground="#6b6358", cursor="hand2",
            highlightthickness=0, bd=0,
        )
        self.save_btn.pack(side="right")

        tk.Button(
            foot, text="关闭", font=self.f_btn,
            bg="#2a2724", fg="#a09585", relief="flat", padx=22, pady=10,
            command=self.root.destroy,
            activebackground="#353230", activeforeground=FG,
            cursor="hand2", highlightthickness=0, bd=0,
        ).pack(side="right", padx=(0, 10))

        # ── 组件齐了，高亮当前配色 ──
        cur = read_scheme()
        if cur:
            for sc in SCHEMES:
                if sc["accent"].lower() == (cur.get("accent") or "").lower():
                    self.select_scheme(sc)
                    break

    # ── 配色页 ─────────────────────────────────

    def build_colors(self, parent):
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="both", expand=True, padx=8, pady=12)

        self.cards = {}
        cols = 4
        for i, sc in enumerate(SCHEMES):
            r, c = divmod(i, cols)
            card = self.make_card(wrap, sc)
            card.grid(row=r, column=c, padx=5, pady=5, sticky="nsew")

        for c in range(cols):
            wrap.columnconfigure(c, weight=1, uniform="card")

    def make_card(self, parent, sc):
        card = tk.Frame(parent, bg=CARD, highlightthickness=2,
                        highlightbackground="#2e2b29")

        cv = tk.Canvas(card, width=148, height=100, bg=sc["bg"],
                       highlightthickness=0, bd=0)
        cv.pack(padx=7, pady=(7, 4))
        self.draw_preview(cv, sc)

        info = tk.Frame(card, bg=CARD)
        info.pack(fill="x", padx=7, pady=(0, 7))
        tk.Label(info, text=sc["name"], font=self.f_name,
                 bg=CARD, fg="#e8e2d9").pack(anchor="w")
        tk.Label(info, text=sc["desc"], font=self.f_desc,
                 bg=CARD, fg=FG2).pack(anchor="w")

        widgets = [card, cv, info] + list(info.winfo_children())
        for w in widgets:
            w.bind("<Button-1>", lambda e, s=sc: self.select_scheme(s))

        card._scheme = sc
        card._canvas = cv
        card._info = info
        self.cards[sc["name"]] = card
        return card

    def draw_preview(self, cv, sc):
        """画迷你界面。Tkinter 的 arc 用 extent（转过角度），没有 end。"""
        cv.create_arc(18, 12, 130, 88, start=200, extent=140,
                      style="arc", outline=sc["surface3"], width=2)
        cv.create_arc(18, 12, 130, 88, start=250, extent=18,
                      style="arc", outline=sc["accent"], width=3)
        cv.create_line(74, 52, 69, 24, fill=sc["accent"], width=2)
        cv.create_oval(70, 48, 78, 56, fill=sc["accent"], outline="")
        cv.create_text(74, 64, text="A", fill=sc["text"],
                       font=("Helvetica", 19, "bold"))
        cv.create_text(74, 82, text="+2", fill=sc["accent"],
                       font=("Helvetica", 8))
        cv.create_rectangle(12, 88, 50, 98, fill=sc["accent"], outline="", width=0)
        cv.create_rectangle(57, 88, 91, 98, fill=sc["surface3"], outline="", width=0)
        cv.create_rectangle(98, 88, 136, 98, fill=sc["surface3"], outline="", width=0)

    def select_scheme(self, scheme):
        self.selected_scheme = scheme

        for name, card in self.cards.items():
            on = (name == scheme["name"])
            bgr = CARD_ON if on else CARD
            card.configure(highlightbackground=scheme["accent"] if on else "#2e2b29",
                           highlightthickness=3 if on else 2, bg=bgr)
            card._info.configure(bg=bgr)
            for w in card._info.winfo_children():
                w.configure(bg=bgr)

        # 保存按钮可能还没建好（初始化阶段），所以先判断
        if hasattr(self, "save_btn"):
            self.refresh_save_btn()
        if hasattr(self, "status"):
            self.status.configure(text=f"已选：{scheme['name']}", fg=scheme["accent"])

    # ── 文字页 ─────────────────────────────────

    def build_texts(self, parent):
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill="both", expand=True, padx=8, pady=10)

        cv = tk.Canvas(outer, bg=BG, highlightthickness=0, bd=0)
        sb = tk.Scrollbar(outer, orient="vertical", command=cv.yview)
        inner = tk.Frame(cv, bg=BG)

        inner.bind("<Configure>",
                   lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0, 0), window=inner, anchor="nw", width=690)
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        current = read_texts()

        # 按分组排列
        groups = []
        for item in TEXT_ITEMS:
            if item["group"] not in groups:
                groups.append(item["group"])

        for g in groups:
            box = tk.Frame(inner, bg=CARD)
            box.pack(fill="x", pady=(0, 10), padx=2)

            tk.Label(box, text=g, font=self.f_group, bg=CARD, fg="#c9c0b4"
                     ).pack(anchor="w", padx=14, pady=(11, 6))

            for item in [i for i in TEXT_ITEMS if i["group"] == g]:
                row = tk.Frame(box, bg=CARD)
                row.pack(fill="x", padx=14, pady=4)

                tk.Label(row, text=item["label"], font=self.f_body,
                         bg=CARD, fg=FG, width=11, anchor="w").pack(side="left")

                var = tk.StringVar(value=current.get(item["key"], ""))
                self.text_vars[item["key"]] = var

                ent = tk.Entry(row, textvariable=var, font=self.f_body,
                               bg="#151312", fg=FG, insertbackground=FG,
                               relief="flat", highlightthickness=1,
                               highlightbackground="#33302c",
                               highlightcolor="#6b6358")
                ent.pack(side="left", fill="x", expand=True, ipady=6, padx=(6, 0))
                ent.bind("<KeyRelease>", lambda e: self.refresh_save_btn())

                if item["hint"]:
                    tk.Label(row, text=item["hint"], font=self.f_small,
                             bg=CARD, fg="#6b6358", width=16, anchor="w"
                             ).pack(side="left", padx=(8, 0))

            tk.Frame(box, bg=CARD, height=8).pack()

    # ── 保存 ───────────────────────────────────

    def refresh_save_btn(self):
        has_scheme = bool(self.selected_scheme)
        has_text = False
        if self.text_vars:
            cur = read_texts()
            for k, v in self.text_vars.items():
                if v.get().strip() and v.get().strip() != cur.get(k, "").strip():
                    has_text = True
                    break

        if has_scheme or has_text:
            self.save_btn.configure(state="normal", bg="#d4a574", fg="#1a1410")
        else:
            self.save_btn.configure(state="disabled", bg="#3a3630", fg="#6b6358")

    def do_save(self):
        done = []

        if self.selected_scheme:
            ok, msg = apply_scheme(self.selected_scheme)
            if ok:
                done.append(f"配色 → {self.selected_scheme['name']}")
            else:
                messagebox.showerror("配色保存失败", msg)
                return

        if self.text_vars:
            values = {k: v.get() for k, v in self.text_vars.items()}
            ok, msg, changed = apply_texts(values)
            if ok and changed:
                done.append(f"文字改了 {len(changed)} 处")
                for c in changed[:6]:
                    done.append(f"   {c}")
            elif not ok:
                messagebox.showerror("文字保存失败", msg)
                return

        if not done:
            self.status.configure(text="没有改动", fg=FG2)
            return

        self.status.configure(text="✓ 已保存", fg="#8fbf7a")
        self.save_btn.configure(state="disabled", bg="#3a3630", fg="#6b6358")

        messagebox.showinfo(
            "保存成功",
            "\n".join(done) + "\n\n"
            "下一步：\n"
            "  1. 双击「预览效果」看真实效果\n"
            "  2. 满意后双击「发布更新」上线",
        )


def main():
    if not os.path.isfile(WEB_FILE):
        print(f"找不到文件：{WEB_FILE}")
        sys.exit(1)

    root = tk.Tk()
    App(root)
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 3)}")
    root.mainloop()


if __name__ == "__main__":
    main()
