import pygame, sys, json, os, math, colorsys
import tkinter as tk
from tkinter import filedialog
import urllib.request
import urllib.error
import threading

pygame.init()
pygame.font.init()

DEFAULT_W, DEFAULT_H = 960, 640
W, H = DEFAULT_W, DEFAULT_H
MIN_W, MIN_H = 700, 480

SIZE_PRESETS = [
    ("Маленький",  800, 540),
    ("Средний",    960, 640),
    ("Большой",   1200, 800),
    ("Огромный",  1400, 900),
]

FPS = 60
PS = 40
SPEED = 8.0

BG1, BG2 = (18, 20, 42), (48, 24, 72)
WHITE = (240, 240, 250); BLACK = (0, 0, 0); GRAY = (90, 95, 120)
DARK = (28, 30, 52); LIGHT = (60, 66, 100)
ACCENT = (90, 200, 255); ACCENT2 = (255, 90, 180)
GOLD = (255, 210, 60); GREEN = (80, 240, 130); RED = (255, 70, 90)
PURPLE = (170, 90, 255); ORANGE = (255, 140, 40)

LANES = [230, 380, 530]

F_HUGE = F_BIG = F_MED = F_SMALL = F_TINY = None

screen = None
clock = pygame.time.Clock()

LEVELS_FILE = "levels.json"
USER_LEVELS_FILE = "user_levels.json"
ACCOUNT_FILE = "account.json"

SERVER_URL = "https://arrow-jump-lvls.vladimirikonov06.workers.dev"
RATING_USER = "vldev"

NET = {"result": None, "error": None, "done": True, "label": ""}

ACCOUNT = {"token": None, "username": None}
USER_LEVELS = []
LEVELS = []

SKINS = {
    "default": {"name": "Классика",   "body": (255,210,60),  "border": (255,140,40)},
    "red":     {"name": "Красный",    "body": (255,70,90),   "border": (150,20,40)},
    "blue":    {"name": "Синий",      "body": (90,200,255),  "border": (30,110,160)},
    "green":   {"name": "Зелёный",    "body": (80,240,130),  "border": (30,140,70)},
    "purple":  {"name": "Фиолетовый", "body": (170,90,255),  "border": (90,40,150)},
    "pink":    {"name": "Розовый",    "body": (255,90,180),  "border": (160,30,100)},
    "orange":  {"name": "Оранжевый",  "body": (255,140,40),  "border": (160,70,10)},
    "ghost":   {"name": "Призрак",    "body": (240,240,250), "border": (150,150,180)},
    "gold":    {"name": "Золото",     "body": (255,210,60),  "border": (140,90,10)},
    "rainbow": {"name": "Радуга",     "body": None,          "border": None},
}
SKIN_ORDER = ["default","red","blue","green","purple","pink","orange","ghost","gold","rainbow"]
CURRENT_SKIN = "default"


def get_skin_colors(skin, t=0):
    if skin not in SKINS:
        skin = "default"
    if skin == "rainbow":
        h = (t * 60) % 360
        r, g, b = colorsys.hsv_to_rgb(h/360, 1.0, 1.0)
        body = (int(r*255), int(g*255), int(b*255))
        r, g, b = colorsys.hsv_to_rgb(((h+180)%360)/360, 1.0, 0.7)
        border = (int(r*255), int(g*255), int(b*255))
        return body, border
    s = SKINS[skin]
    return s["body"], s["border"]


def draw_skin_dot(sc, x, y, r, skin, t=0):
    body, border = get_skin_colors(skin, t)
    pygame.draw.circle(sc, border, (x, y), r + 2)
    pygame.draw.circle(sc, body, (x, y), r)


def draw_stars(sc, x, y, rating, size=18):
    for i in range(5):
        cx = x + i * (size + 3)
        cy = y
        color = GOLD if i < rating else (60, 60, 80)
        pts = []
        for k in range(10):
            ang = -math.pi / 2 + k * math.pi / 5
            rad = size // 2 if k % 2 == 0 else size // 4
            pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
        pygame.draw.polygon(sc, color, pts)
        pygame.draw.polygon(sc, BLACK, pts, 1)


def init_window(w, h):
    global W, H, screen, F_HUGE, F_BIG, F_MED, F_SMALL, F_TINY, LANES
    W, H = w, h
    screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
    pygame.display.set_caption("Arrow Jump")
    F_HUGE = pygame.font.SysFont("Arial", max(28, int(h * 0.10)), bold=True)
    F_BIG = pygame.font.SysFont("Arial", max(20, int(h * 0.060)), bold=True)
    F_MED = pygame.font.SysFont("Arial", max(16, int(h * 0.040)), bold=True)
    F_SMALL = pygame.font.SysFont("Arial", max(13, int(h * 0.030)))
    F_TINY = pygame.font.SysFont("Arial", max(10, int(h * 0.022)))
    top = int(h * 0.36)
    bot = int(h * 0.82)
    LANES = [top, (top + bot) // 2, bot]


def parse_link(text):
    text = (text or "").strip()
    if not text:
        return (None, None)
    if text.isdigit() and len(text) == 6:
        return ("level", text)
    if text.lower().startswith("arrowjump://"):
        rest = text[len("arrowjump://"):]
        if rest.startswith("level/"):
            code = rest[len("level/"):]
            if code.isdigit() and len(code) == 6:
                return ("level", code)
        if rest.startswith("user/"):
            name = rest[len("user/"):].strip("/")
            if name:
                return ("user", name)
    if "/l/" in text:
        code = text.rsplit("/l/", 1)[1].split("?")[0].split("/")[0]
        if code.isdigit() and len(code) == 6:
            return ("level", code)
    if "/level/" in text:
        code = text.rsplit("/level/", 1)[1].split("?")[0].split("/")[0]
        if code.isdigit() and len(code) == 6:
            return ("level", code)
    if "/u/" in text:
        name = text.rsplit("/u/", 1)[1].split("?")[0].split("/")[0]
        if name:
            return ("user", name)
    if "/user/" in text:
        name = text.rsplit("/user/", 1)[1].split("?")[0].split("/")[0]
        if name:
            return ("user", name)
    if all(c.isalnum() or c == "_" for c in text) and 3 <= len(text) <= 20:
        return ("user", text)
    return (None, None)


def make_share_link(kind, value):
    if kind == "level":
        return f"arrowjump://level/{value}"
    if kind == "user":
        return f"arrowjump://user/{value}"
    return ""


def make_web_link(kind, value):
    if kind == "level":
        return f"{SERVER_URL}/l/{value}"
    if kind == "user":
        return f"{SERVER_URL}/u/{value}"
    return SERVER_URL


def copy_to_clipboard(text):
    try:
        r = tk.Tk(); r.withdraw()
        r.clipboard_clear(); r.clipboard_append(text)
        r.update(); r.destroy()
        return True
    except Exception:
        return False


def mk(name, diff, obs, length):
    return {"name": name, "difficulty": diff, "length": length, "obstacles": obs}


def defaults():
    L = []
    obs, x = [], 700
    for i in range(14):
        obs.append({"x": x, "lane": i % 3, "type": "spike"})
        if i % 2 == 0:
            obs.append({"x": x + 60, "lane": (i + 1) % 3, "type": "coin"})
        x += 420
    L.append(mk("Stereo Start", "Easy", obs, x + 600))
    obs, x = [], 700
    for i in range(18):
        l = (i * 2) % 3
        obs.append({"x": x, "lane": l, "type": "block"})
        obs.append({"x": x + 90, "lane": (l + 2) % 3, "type": "coin"})
        if i % 3 == 0:
            obs.append({"x": x + 180, "lane": (l + 1) % 3, "type": "spike"})
        x += 400
    L.append(mk("Neon Path", "Easy", obs, x + 600))
    obs, x = [], 650
    for i in range(24):
        l = (i * 2 + i // 4) % 3
        obs.append({"x": x, "lane": l, "type": "spike"})
        obs.append({"x": x + 130, "lane": (l + 1) % 3, "type": "spike"})
        if i % 2 == 1:
            obs.append({"x": x + 250, "lane": (l + 2) % 3, "type": "coin"})
        if i % 4 == 0:
            obs.append({"x": x + 320, "lane": (l + 1) % 3, "type": "jump"})
        x += 480
    L.append(mk("Side Runner", "Normal", obs, x + 700))
    obs, x = [], 650
    for i in range(28):
        l = (i * 2) % 3
        obs.append({"x": x, "lane": l, "type": "block"})
        obs.append({"x": x + 100, "lane": (l + 1) % 3, "type": "spike"})
        obs.append({"x": x + 200, "lane": (l + 2) % 3, "type": "block"})
        if i % 2 == 0:
            obs.append({"x": x + 300, "lane": l, "type": "coin"})
        if i % 3 == 0:
            obs.append({"x": x + 380, "lane": (l + 1) % 3, "type": "speed"})
        x += 520
    L.append(mk("Crazy Tracks", "Normal", obs, x + 700))
    obs, x = [], 600
    for i in range(34):
        l = (i * 2 + i // 3) % 3
        obs.append({"x": x, "lane": l, "type": "spike"})
        obs.append({"x": x + 80, "lane": (l + 1) % 3, "type": "block"})
        obs.append({"x": x + 160, "lane": (l + 2) % 3, "type": "spike"})
        if i % 2 == 0:
            obs.append({"x": x + 240, "lane": (l + 1) % 3, "type": "coin"})
        x += 420
    L.append(mk("Hyper Rush", "Hard", obs, x + 700))
    obs, x = [], 600
    for i in range(45):
        l = (i * 2 + i // 2) % 3
        obs.append({"x": x, "lane": l, "type": "spike"})
        obs.append({"x": x + 70, "lane": (l + 1) % 3, "type": "spike"})
        obs.append({"x": x + 140, "lane": (l + 2) % 3, "type": "block"})
        obs.append({"x": x + 210, "lane": (l + 1) % 3, "type": "coin"})
        if i % 3 == 0:
            obs.append({"x": x + 290, "lane": l, "type": "jump"})
        if i % 4 == 0:
            obs.append({"x": x + 350, "lane": (l + 2) % 3, "type": "speed"})
        x += 420
    L.append(mk("Demon Core", "Insane", obs, x + 700))
    return L


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_levels():
    return load_json(LEVELS_FILE, defaults())

def load_user_levels():
    return load_json(USER_LEVELS_FILE, [])

def save_levels(lv):
    save_json(LEVELS_FILE, lv)

def save_user_levels(lv):
    save_json(USER_LEVELS_FILE, lv)


def load_account():
    global ACCOUNT, CURRENT_SKIN
    ACCOUNT = load_json(ACCOUNT_FILE, {"token": None, "username": None})
    CURRENT_SKIN = ACCOUNT.get("skin", "default")


def save_account():
    ACCOUNT["skin"] = CURRENT_SKIN
    save_json(ACCOUNT_FILE, ACCOUNT)


def sanitize_level(lvl, fallback_name="Импорт"):
    if not isinstance(lvl, dict):
        return None
    obs = []
    for o in lvl.get("obstacles", []):
        if not isinstance(o, dict):
            continue
        if not all(k in o for k in ("x", "lane", "type")):
            continue
        try:
            x = int(o["x"]); ln = int(o["lane"])
        except Exception:
            continue
        if ln not in (0, 1, 2):
            continue
        if o["type"] not in ("spike", "block", "coin", "jump", "speed"):
            continue
        obs.append({"x": x, "lane": ln, "type": o["type"]})
    res = mk(lvl.get("name", fallback_name),
             lvl.get("difficulty", "Normal"),
             obs, int(lvl.get("length", 5000)))
    for k in ("author", "authorSkin", "code", "rating"):
        if lvl.get(k) is not None:
            res[k] = lvl[k]
    return res


def import_dialog():
    root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
    p = filedialog.askopenfilename(
        title="Импорт уровней",
        filetypes=[("JSON", "*.json"), ("Все файлы", "*.*")])
    root.destroy()
    if not p:
        return None, "Отменено"
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as ex:
        return None, f"Ошибка: {ex}"
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return None, "Неверный формат"
    out = []
    for i, lvl in enumerate(data):
        s = sanitize_level(lvl, f"Импорт {i+1}")
        if s:
            out.append(s)
    if not out:
        return None, "Нет валидных уровней"
    return out, f"Импортировано: {len(out)}"


def _req(method, path, body=None, token=None):
    url = SERVER_URL + path
    headers = {
        "Content-Type": "application/json",
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru,en;q=0.9",
        "Origin": SERVER_URL,
        "Referer": SERVER_URL + "/",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            msg = err_body.get("error", f"HTTP {e.code}")
        except Exception:
            msg = f"HTTP {e.code}"
        return None, msg
    except Exception as e:
        return None, str(e)


def start_net(label, fn):
    def worker():
        try:
            res, err = fn()
            NET["result"] = res
            NET["error"] = err
        except Exception as ex:
            NET["result"] = None
            NET["error"] = str(ex)
        NET["done"] = True
        NET["label"] = label
    NET["done"] = False
    NET["label"] = label
    threading.Thread(target=worker, daemon=True).start()


def net_upload(level):
    return start_net("upload", lambda: _req("POST", "/upload", level, ACCOUNT["token"]))

def net_download(code):
    return start_net("download", lambda: _req("GET", f"/level/{code}"))

def net_register(u, p):
    return start_net("register", lambda: _req("POST", "/register", {"username": u, "password": p}))

def net_login(u, p):
    return start_net("login", lambda: _req("POST", "/login", {"username": u, "password": p}))

def net_my_levels(u):
    return start_net("mylevels", lambda: _req("GET", f"/my-levels/{u}"))

def net_featured():
    return start_net("featured", lambda: _req("GET", "/featured"))

def net_top():
    return start_net("top", lambda: _req("GET", "/top"))

def net_users():
    return start_net("users", lambda: _req("GET", "/users"))

def net_user_profile(u):
    return start_net("profile", lambda: _req("GET", f"/user/{u}"))

def net_set_skin(skin):
    return start_net("set_skin", lambda: _req("POST", "/set-skin", {"skin": skin}, ACCOUNT["token"]))

def net_rename(code, name):
    return start_net("rename", lambda: _req("POST", "/rename", {"code": code, "name": name}, ACCOUNT["token"]))

def net_rate(code, stars):
    return start_net("rate", lambda: _req("POST", "/rate", {"code": code, "stars": stars}, ACCOUNT["token"]))


def net_load_all_full():
    """Скачивает ВСЕ уровни с сервера полностью."""
    def worker():
        try:
            meta, err = _req("GET", "/featured")
            if err:
                NET["result"] = None
                NET["error"] = err
                NET["done"] = True
                NET["label"] = "load_all"
                return
            if not isinstance(meta, list):
                NET["result"] = []
                NET["done"] = True
                NET["label"] = "load_all"
                return
            out = []
            for item in meta:
                code = item.get("code")
                if not code:
                    continue
                full, err2 = _req("GET", f"/level/{code}")
                if full:
                    s = sanitize_level(full, "С сервера")
                    if s:
                        out.append(s)
            NET["result"] = out
            NET["error"] = None
        except Exception as ex:
            NET["result"] = None
            NET["error"] = str(ex)
        NET["done"] = True
        NET["label"] = "load_all"
    NET["done"] = False
    NET["label"] = "load_all"
    threading.Thread(target=worker, daemon=True).start()


class Btn:
    def __init__(self, r, t, c=ACCENT, tc=BLACK, f=None):
        self.rect = pygame.Rect(r)
        self.text = t
        self.color = c
        self.tc = tc
        self.font = f or F_MED
        self.hover = False

    def handle(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(e.pos)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.rect.collidepoint(e.pos):
                return True
        return False

    def draw(self, sc):
        c = self.color
        if self.hover:
            c = tuple(min(255, x + 30) for x in c)
        r = self.rect.copy()
        if self.hover:
            r.inflate_ip(4, 4)
        pygame.draw.rect(sc, BLACK, r, border_radius=10)
        pygame.draw.rect(sc, c, r, border_radius=8)
        t = self.font.render(self.text, True, self.tc)
        sc.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))


class TextInput:
    def __init__(self, rect, placeholder="", mask=False, initial=""):
        self.rect = pygame.Rect(rect)
        self.text = initial
        self.placeholder = placeholder
        self.mask = mask
        self.active = True

    def handle(self, e):
        if e.type == pygame.KEYDOWN and self.active:
            if e.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif e.key == pygame.K_RETURN:
                return self.text
            elif e.unicode and e.unicode.isprintable() and len(self.text) < 40:
                self.text += e.unicode
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.active = self.rect.collidepoint(e.pos)
        return None

    def draw(self, sc):
        pygame.draw.rect(sc, DARK, self.rect, border_radius=8)
        pygame.draw.rect(sc, ACCENT if self.active else GRAY, self.rect, 2, border_radius=8)
        display = "*" * len(self.text) if self.mask else self.text
        if not display:
            display = self.placeholder
            col = (140, 150, 180)
        else:
            col = WHITE
        t = F_MED.render(display, True, col)
        sc.blit(t, (self.rect.x + 12, self.rect.centery - t.get_height() // 2))


def bg(sc, t=0, cam=0):
    for y in range(H):
        k = y / H
        c = (int(BG1[0] + (BG2[0] - BG1[0]) * k),
             int(BG1[1] + (BG2[1] - BG1[1]) * k),
             int(BG1[2] + (BG2[2] - BG1[2]) * k))
        pygame.draw.line(sc, c, (0, y), (W, y))
    for i in range(80):
        sx = (i * 137 - cam * 0.15 + t * 0.4) % (W + 100) - 50
        sy = (i * 83) % (H - 100)
        pygame.draw.circle(sc, (170, 180, 220), (int(sx), sy), 1 + (i % 2))


def draw_obj(sc, ox, oy, t):
    if t == "spike":
        p = [(ox - 20, oy + 22), (ox, oy - 22), (ox + 20, oy + 22)]
        pygame.draw.polygon(sc, RED, p)
        pygame.draw.polygon(sc, (255, 170, 180), p, 2)
    elif t == "block":
        r = pygame.Rect(ox - 22, oy - 22, 44, 44)
        pygame.draw.rect(sc, PURPLE, r, border_radius=6)
        pygame.draw.rect(sc, (220, 170, 255), r, 3, border_radius=6)
    elif t == "coin":
        b = math.sin(pygame.time.get_ticks() / 200 + ox) * 4
        pygame.draw.circle(sc, GOLD, (int(ox), int(oy + b)), 14)
        pygame.draw.circle(sc, ORANGE, (int(ox), int(oy + b)), 14, 2)
    elif t == "jump":
        p = [(ox - 18, oy + 18), (ox, oy - 18), (ox + 18, oy + 18)]
        pygame.draw.polygon(sc, GREEN, p)
        pygame.draw.polygon(sc, (180, 255, 200), p, 2)
    elif t == "speed":
        pygame.draw.circle(sc, ACCENT2, (int(ox), int(oy)), 16)
        pygame.draw.polygon(sc, WHITE, [(ox - 6, oy - 8), (ox + 6, oy), (ox - 6, oy + 8)])


def draw_account_badge(sc):
    if ACCOUNT["username"]:
        t = F_SMALL.render(f"@{ACCOUNT['username']}", True, GOLD)
        draw_skin_dot(sc, W - t.get_width() - 35, 24, 8, CURRENT_SKIN,
                      pygame.time.get_ticks() / 1000)
        sc.blit(t, (W - t.get_width() - 20, 15))


def menu():
    global W, H, screen
    btns = [("play",   Btn((W // 2 - 170, int(H * 0.26), 340, 50), "ИГРАТЬ", GREEN)),
            ("edit",   Btn((W // 2 - 170, int(H * 0.26) + 60, 340, 50), "РЕДАКТОР", ACCENT)),
            ("links",  Btn((W // 2 - 170, int(H * 0.26) + 120, 340, 50), "ССЫЛКИ", GOLD)),
            ("acc",    Btn((W // 2 - 170, int(H * 0.26) + 180, 340, 50), "АККАУНТ", ACCENT2)),
            ("donate", Btn((W // 2 - 170, int(H * 0.26) + 240, 340, 50), "💎 ПОДДЕРЖАТЬ", ACCENT2)),
            ("sett",   Btn((W // 2 - 170, int(H * 0.26) + 300, 340, 50), "НАСТРОЙКИ", ORANGE)),
            ("quit",   Btn((W // 2 - 170, int(H * 0.26) + 360, 340, 50), "ВЫХОД", RED))]
    while True:
        clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.VIDEORESIZE:
                W = max(MIN_W, e.w); H = max(MIN_H, e.h)
                init_window(W, H)
                return menu()
            for k, b in btns:
                if b.handle(e):
                    return k
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()
        bg(screen, pygame.time.get_ticks() / 1000)
        t = F_HUGE.render("ARROW JUMP", True, GOLD)
        screen.blit(t, (W // 2 - t.get_width() // 2, int(H * 0.06)))
        t = F_MED.render("3 дорожки · вверх / середина / низ", True, WHITE)
        screen.blit(t, (W // 2 - t.get_width() // 2, int(H * 0.18)))
        for _, b in btns:
            b.draw(screen)
        draw_account_badge(screen)
        hint = F_TINY.render("W/S или ↑/↓ — переключение дорожки | ESC — выход",
                             True, (180, 190, 220))
        screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 30))
        pygame.display.flip()


def settings_screen():
    global W, H, screen
    presets_btns = []
    for i, (label, pw, ph) in enumerate(SIZE_PRESETS):
        presets_btns.append((i, Btn((W // 2 - 200, int(H * 0.28) + i * 60, 400, 50),
                                    f"{label}  ({pw}×{ph})", ACCENT, BLACK, F_MED)))
    back = Btn((W // 2 - 100, H - 90, 200, 55), "НАЗАД", GRAY, WHITE, F_MED)
    while True:
        clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.VIDEORESIZE:
                W = max(MIN_W, e.w); H = max(MIN_H, e.h)
                init_window(W, H)
                return settings_screen()
            if back.handle(e):
                return "menu"
            for i, b in presets_btns:
                if b.handle(e):
                    label, pw, ph = SIZE_PRESETS[i]
                    init_window(pw, ph)
                    return settings_screen()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return "menu"
        bg(screen, pygame.time.get_ticks() / 1000)
        t = F_BIG.render("НАСТРОЙКИ ОКНА", True, WHITE)
        screen.blit(t, (W // 2 - t.get_width() // 2, int(H * 0.12)))
        info = F_SMALL.render("Выбери пресет или растяни окно мышью", True, (180, 190, 220))
        screen.blit(info, (W // 2 - info.get_width() // 2, int(H * 0.18)))
        for _, b in presets_btns:
            b.draw(screen)
        cur = F_SMALL.render(f"Текущий размер: {W}×{H}", True, GOLD)
        screen.blit(cur, (W // 2 - cur.get_width() // 2, H - 160))
        back.draw(screen)
        pygame.display.flip()


def account_screen():
    global W, H, screen, ACCOUNT, CURRENT_SKIN
    msg = ""
    msg_t = 0

    user_in = TextInput((W // 2 - 200, int(H * 0.28), 400, 50), "логин")
    pass_in = TextInput((W // 2 - 200, int(H * 0.28) + 70, 400, 50), "пароль", mask=True)

    while True:
        login_btn = Btn((W // 2 - 200, int(H * 0.28) + 150, 190, 50), "ВОЙТИ", GREEN, BLACK, F_MED)
        reg_btn = Btn((W // 2 + 10, int(H * 0.28) + 150, 190, 50), "РЕГИСТРАЦИЯ", ACCENT, BLACK, F_MED)
        logout_btn = Btn((W // 2 - 200, int(H * 0.28) + 150, 400, 50), "ВЫЙТИ ИЗ АККАУНТА", RED, WHITE, F_MED)
        copy_btn = Btn((W // 2 - 200, int(H * 0.28) + 220, 190, 50), "МОЯ ССЫЛКА", ACCENT2, BLACK, F_SMALL)
        site_btn = Btn((W // 2 + 10, int(H * 0.28) + 220, 190, 50), "МОЙ САЙТ", GOLD, BLACK, F_SMALL)
        back = Btn((W // 2 - 100, H - 70, 200, 50), "НАЗАД", GRAY, WHITE, F_MED)

        skin_btns = []
        if ACCOUNT["username"]:
            base_y = int(H * 0.52)
            cols = 5
            for i, sk in enumerate(SKIN_ORDER):
                col = i % cols
                row = i // cols
                x = W // 2 - 400 + col * 165
                y = base_y + row * 55
                skin_btns.append((sk, Btn((x, y, 150, 45), SKINS[sk]["name"], LIGHT, WHITE, F_TINY)))

        clock.tick(FPS)
        resize_break = False
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.VIDEORESIZE:
                W = max(MIN_W, e.w); H = max(MIN_H, e.h)
                init_window(W, H)
                resize_break = True
                break
            if back.handle(e):
                return "menu"
            if ACCOUNT["username"]:
                if logout_btn.handle(e):
                    ACCOUNT = {"token": None, "username": None}
                    CURRENT_SKIN = "default"
                    save_account()
                    msg = "Вы вышли"; msg_t = 120
                if copy_btn.handle(e):
                    link = make_share_link("user", ACCOUNT["username"])
                    if copy_to_clipboard(link):
                        msg = f"Скопировано: {link}"
                    else:
                        msg = link
                    msg_t = 180
                if site_btn.handle(e):
                    url = make_web_link("user", ACCOUNT["username"])
                    if copy_to_clipboard(url):
                        msg = f"Ссылка на сайт: {url}"
                    else:
                        msg = url
                    msg_t = 200
                for sk, b in skin_btns:
                    if b.handle(e) and NET["done"]:
                        net_set_skin(sk)
                        msg = "Сохранение скина..."; msg_t = 60
            else:
                user_in.handle(e)
                pass_in.handle(e)
                submit = (e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN
                          and (user_in.active or pass_in.active))
                if login_btn.handle(e) or submit:
                    if user_in.text and pass_in.text and NET["done"]:
                        net_login(user_in.text, pass_in.text)
                        msg = "Вход..."; msg_t = 60
                if reg_btn.handle(e):
                    if user_in.text and pass_in.text and NET["done"]:
                        net_register(user_in.text, pass_in.text)
                        msg = "Регистрация..."; msg_t = 60
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return "menu"

        if resize_break:
            continue

        if NET["done"] and NET["label"] in ("login", "register"):
            if NET["result"] and "token" in NET["result"]:
                ACCOUNT["token"] = NET["result"]["token"]
                ACCOUNT["username"] = NET["result"]["username"]
                CURRENT_SKIN = NET["result"].get("skin", "default")
                save_account()
                msg = f"Добро пожаловать, {ACCOUNT['username']}!"
                msg_t = 240
                NET["result"] = None
                user_in.text = ""
                pass_in.text = ""
            elif NET["error"]:
                msg = f"Ошибка: {NET['error']}"
                msg_t = 240
                NET["error"] = None

        if NET["done"] and NET["label"] == "set_skin":
            if NET["result"] and NET["result"].get("skin"):
                CURRENT_SKIN = NET["result"]["skin"]
                save_account()
                msg = f"Скин: {SKINS[CURRENT_SKIN]['name']}"
                msg_t = 180
                NET["result"] = None
            elif NET["error"]:
                msg = f"Ошибка: {NET['error']}"
                msg_t = 180
                NET["error"] = None

        if msg_t > 0:
            msg_t -= 1

        bg(screen, pygame.time.get_ticks() / 1000)
        t = F_BIG.render("АККАУНТ", True, WHITE)
        screen.blit(t, (W // 2 - t.get_width() // 2, 30))

        if ACCOUNT["username"]:
            draw_skin_dot(screen, W // 2 - 120, int(H * 0.24), 25, CURRENT_SKIN,
                          pygame.time.get_ticks() / 1000)
            info = F_MED.render(f"@{ACCOUNT['username']}", True, GOLD)
            screen.blit(info, (W // 2 - 80, int(H * 0.24) - info.get_height() // 2))

            if ACCOUNT["username"] == RATING_USER:
                badge = F_SMALL.render("★ РЕЙТИНГ-МАСТЕР ★", True, GOLD)
                screen.blit(badge, (W // 2 + 60, int(H * 0.24) - 10))

            link1 = F_TINY.render("arrowjump://user/" + ACCOUNT["username"], True, (180, 190, 220))
            screen.blit(link1, (W // 2 - 200, int(H * 0.28) + 60))

            copy_btn.draw(screen)
            site_btn.draw(screen)
            logout_btn.draw(screen)

            skin_title = F_MED.render("ВЫБЕРИ СКИН", True, WHITE)
            screen.blit(skin_title, (W // 2 - skin_title.get_width() // 2, int(H * 0.47)))
            for sk, b in skin_btns:
                b.draw(screen)
                body, border = get_skin_colors(sk, pygame.time.get_ticks() / 1000)
                pygame.draw.circle(screen, border, (b.rect.x + 20, b.rect.centery), 10)
                pygame.draw.circle(screen, body, (b.rect.x + 20, b.rect.centery), 8)
                if sk == CURRENT_SKIN:
                    pygame.draw.rect(screen, GOLD, b.rect.inflate(6, 6), 3, border_radius=8)
        else:
            info = F_SMALL.render("Войди или зарегистрируйся", True, (180, 190, 220))
            screen.blit(info, (W // 2 - info.get_width() // 2, int(H * 0.21)))
            user_in.draw(screen)
            pass_in.draw(screen)
            login_btn.draw(screen)
            reg_btn.draw(screen)

        back.draw(screen)

        if msg_t > 0:
            mt = F_SMALL.render(msg, True, GREEN)
            rr = pygame.Rect(W // 2 - mt.get_width() // 2 - 20, H - 130,
                             mt.get_width() + 40, 40)
            pygame.draw.rect(screen, DARK, rr, border_radius=10)
            pygame.draw.rect(screen, GREEN, rr, 2, border_radius=10)
            screen.blit(mt, (W // 2 - mt.get_width() // 2, H - 122))

        pygame.display.flip()


def level_select(mode="play"):
    global W, H, screen, USER_LEVELS
    builtin = load_levels()
    USER_LEVELS = load_user_levels()
    tab = "builtin"
    scroll = 0
    code_in = None
    msg = ""
    msg_t = 0

    while True:
        back = Btn((20, H - 70, 150, 50), "← НАЗАД", GRAY, WHITE, F_SMALL)
        imp = Btn((W - 400, H - 70, 170, 50), "ИМПОРТ", ORANGE, BLACK, F_SMALL)
        dl = Btn((W - 580, H - 70, 170, 50), "СКАЧАТЬ", ACCENT2, BLACK, F_SMALL)
        my = Btn((W - 760, H - 70, 170, 50), "ВСЕ С СЕРВЕРА", GREEN, BLACK, F_SMALL)
        tab_builtin = Btn((100, 100, 260, 44), "ВСТРОЕННЫЕ", GOLD, BLACK, F_SMALL)
        tab_user = Btn((370, 100, 260, 44), "ПОЛЬЗОВАТЕЛЬСКИЕ", ACCENT, BLACK, F_SMALL)

        items = builtin if tab == "builtin" else USER_LEVELS
        rows = []
        y = 180 - scroll
        for i in range(len(items)):
            rows.append((i, Btn((W - 200, y + 22, 130, 46),
                                "ИГРАТЬ" if mode == "play" else "РЕДАКТ.",
                                ACCENT, BLACK, F_SMALL)))
            y += 110

        clock.tick(FPS)
        resize_break = False
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.VIDEORESIZE:
                W = max(MIN_W, e.w); H = max(MIN_H, e.h)
                init_window(W, H)
                resize_break = True
                break

            if code_in is not None:
                res = code_in.handle(e)
                if res is not None:
                    kind, val = parse_link(res)
                    if kind == "level" and NET["done"]:
                        net_download(val)
                        msg = "Скачивание..."; msg_t = 60
                    elif kind == "user" and NET["done"]:
                        net_user_profile(val)
                        msg = "Профиль..."; msg_t = 60
                    code_in = None
                    continue
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    code_in = None
                    continue
                if e.type == pygame.MOUSEBUTTONDOWN and not code_in.rect.collidepoint(e.pos):
                    code_in = None
                continue

            if back.handle(e):
                return ("back", None)
            if tab_builtin.handle(e):
                tab = "builtin"; scroll = 0
            if tab_user.handle(e):
                tab = "user"; scroll = 0
            if imp.handle(e):
                nl, text = import_dialog()
                if nl:
                    if tab == "user":
                        USER_LEVELS.extend(nl)
                        save_user_levels(USER_LEVELS)
                    else:
                        builtin.extend(nl)
                        save_levels(builtin)
                msg = text; msg_t = 120
            if dl.handle(e):
                code_in = TextInput((W // 2 - 220, H // 2 - 30, 440, 60),
                                    "код или arrowjump://...")
            if my.handle(e):
                net_load_all_full()
                msg = "Загрузка всех уровней с сервера..."; msg_t = 60
            if e.type == pygame.MOUSEWHEEL:
                scroll = max(0, min(max(0, len(items) * 110 - (H - 240)), scroll - e.y * 40))
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return ("back", None)
                if e.key == pygame.K_i:
                    nl, text = import_dialog()
                    if nl:
                        if tab == "user":
                            USER_LEVELS.extend(nl)
                            save_user_levels(USER_LEVELS)
                        else:
                            builtin.extend(nl)
                            save_levels(builtin)
                    msg = text; msg_t = 120
                if e.key == pygame.K_o:
                    code_in = TextInput((W // 2 - 220, H // 2 - 30, 440, 60),
                                        "код или arrowjump://...")
                if e.key == pygame.K_r:
                    net_load_all_full()
                    msg = "Загрузка всех уровней с сервера..."; msg_t = 60
                if e.key == pygame.K_TAB:
                    tab = "user" if tab == "builtin" else "builtin"
                    scroll = 0
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my_pos = e.pos
                for idx, b in rows:
                    if b.rect.collidepoint(mx, my_pos):
                        return ("pick", (idx, tab))
                y2 = 180 - scroll
                for i in range(len(items)):
                    if pygame.Rect(100, y2, W - 200, 90).collidepoint(mx, my_pos):
                        return ("pick", (i, tab))
                    y2 += 110

        if resize_break:
            continue

        if NET["done"] and NET["label"] == "download" and NET["result"] is not None:
            s = sanitize_level(NET["result"], "С сервера")
            if s:
                # если уже есть с таким кодом — заменить, иначе добавить
                code = s.get("code")
                replaced = False
                if code:
                    for i, u in enumerate(USER_LEVELS):
                        if u.get("code") == code:
                            USER_LEVELS[i] = s
                            replaced = True
                            break
                if not replaced:
                    USER_LEVELS.append(s)
                save_user_levels(USER_LEVELS)
                tab = "user"
                msg = "Уровень добавлен!"
            else:
                msg = "Неверный ответ сервера"
            msg_t = 200
            NET["result"] = None
            NET["error"] = None
        elif NET["done"] and NET["label"] == "download" and NET["error"]:
            msg = f"Ошибка: {NET['error']}"
            msg_t = 200
            NET["error"] = None

        if NET["done"] and NET["label"] == "load_all":
            if NET["result"] is not None:
                data = NET["result"]
                if isinstance(data, list):
                    USER_LEVELS.clear()
                    USER_LEVELS.extend(data)
                    save_user_levels(USER_LEVELS)
                    tab = "user"
                    msg = f"Загружено с сервера: {len(data)} уровней"
                    msg_t = 240
                else:
                    msg = "Ошибка: список пустой"
                    msg_t = 200
                NET["result"] = None
                NET["error"] = None
            elif NET["error"]:
                msg = f"Ошибка: {NET['error']}"
                msg_t = 240
                NET["error"] = None

        if NET["done"] and NET["label"] == "profile" and NET["result"] is not None:
            return ("profile", NET["result"])

        if msg_t > 0:
            msg_t -= 1

        bg(screen, pygame.time.get_ticks() / 1000)
        title = "ВЫБОР УРОВНЯ" if mode == "play" else "РЕДАКТОР"
        t = F_BIG.render(title, True, WHITE)
        screen.blit(t, (W // 2 - t.get_width() // 2, 40))

        tab_builtin.draw(screen)
        tab_user.draw(screen)
        active_rect = tab_builtin.rect if tab == "builtin" else tab_user.rect
        pygame.draw.rect(screen, WHITE, active_rect.inflate(8, 8), 3, border_radius=12)

        mx, my_pos = pygame.mouse.get_pos()
        y = 180 - scroll
        for i, lvl in enumerate(items):
            r = pygame.Rect(100, y, W - 200, 90)
            if r.bottom > 120 and r.top < H - 100:
                hover = r.collidepoint(mx, my_pos)
                pygame.draw.rect(screen, (55, 60, 95) if hover else (35, 40, 68), r, border_radius=14)
                pygame.draw.rect(screen, ACCENT if hover else LIGHT, r, 3, border_radius=14)
                num = F_BIG.render(str(i + 1), True, GOLD)
                screen.blit(num, (r.x + 30, r.centery - num.get_height() // 2))
                nm = F_MED.render(lvl["name"], True, WHITE)
                screen.blit(nm, (r.x + 110, r.y + 10))
                d = lvl.get("difficulty", "Normal")
                dc = {"Easy": GREEN, "Normal": GOLD, "Hard": ORANGE, "Insane": RED}.get(d, WHITE)
                screen.blit(F_SMALL.render(d, True, dc), (r.x + 110, r.y + 40))
                rating = lvl.get("rating", 0)
                draw_stars(screen, r.x + 110, r.y + 68, rating, size=14)
                c = F_SMALL.render(f"Объектов: {len(lvl['obstacles'])}", True, (180, 190, 220))
                screen.blit(c, (r.x + 320, r.y + 16))
                ln = F_SMALL.render(f"Длина: {lvl['length']}", True, (180, 190, 220))
                screen.blit(ln, (r.x + 320, r.y + 42))
                if lvl.get("author"):
                    draw_skin_dot(screen, r.right - 220, r.y + 70, 8,
                                  lvl.get("authorSkin", "default"),
                                  pygame.time.get_ticks() / 1000)
                    au = F_TINY.render(f"@{lvl['author']}", True, GOLD)
                    screen.blit(au, (r.right - 200, r.y + 62))
                if lvl.get("code"):
                    cd = F_TINY.render(f"code: {lvl['code']}", True, ACCENT)
                    screen.blit(cd, (r.right - 220, r.y + 40))
            y += 110

        if tab == "user" and not items:
            empty = F_MED.render("Пусто. Нажми ВСЕ С СЕРВЕРА или залей свой через редактор.",
                                 True, (160, 170, 200))
            screen.blit(empty, (W // 2 - empty.get_width() // 2, H // 2))

        for _, b in rows:
            b.draw(screen)
        back.draw(screen)
        imp.draw(screen)
        dl.draw(screen)
        my.draw(screen)
        draw_account_badge(screen)

        if msg_t > 0:
            mt = F_SMALL.render(msg, True, GREEN)
            rr = pygame.Rect(W // 2 - mt.get_width() // 2 - 20, H - 130,
                             mt.get_width() + 40, 42)
            pygame.draw.rect(screen, DARK, rr, border_radius=10)
            pygame.draw.rect(screen, GREEN, rr, 2, border_radius=10)
            screen.blit(mt, (W // 2 - mt.get_width() // 2, H - 122))

        if code_in is not None:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 180))
            screen.blit(ov, (0, 0))
            t = F_MED.render("Код, ссылка на уровень или профиль", True, WHITE)
            screen.blit(t, (W // 2 - t.get_width() // 2, H // 2 - 90))
            code_in.draw(screen)
            t2 = F_TINY.render("ENTER — открыть | ESC — отмена", True, (200, 200, 220))
            screen.blit(t2, (W // 2 - t2.get_width() // 2, H // 2 + 50))

        hint = F_TINY.render("TAB — вкладка | I — импорт | O — по ссылке | R — все с сервера | ESC — назад",
                             True, (160, 170, 200))
        screen.blit(hint, (W - 620, H - 92))
        pygame.display.flip()


def links_screen():
    global W, H, screen, USER_LEVELS
    tab = "levels"
    items = []
    scroll = 0
    msg = ""
    msg_t = 0
    link_in = TextInput((W // 2 - 260, 150, 520, 50), "вставь arrowjump://... или код")
    net_featured()

    while True:
        back = Btn((20, H - 70, 150, 50), "← НАЗАД", GRAY, WHITE, F_SMALL)
        refresh = Btn((W - 230, H - 70, 210, 50), "ОБНОВИТЬ", ACCENT, BLACK, F_SMALL)
        tab_lvl = Btn((100, 100, 200, 44), "УРОВНИ", GOLD, BLACK, F_SMALL)
        tab_top = Btn((310, 100, 200, 44), "⭐ ТОП", GOLD, BLACK, F_SMALL)
        tab_usr = Btn((520, 100, 200, 44), "ИГРОКИ", ACCENT2, BLACK, F_SMALL)
        go_btn = Btn((W // 2 + 270, 150, 140, 50), "ОТКРЫТЬ", GREEN, BLACK, F_SMALL)

        rows = []
        y = 220 - scroll
        for i in range(len(items)):
            rows.append((i, Btn((W - 200, y + 22, 130, 46), "ОТКРЫТЬ",
                                ACCENT, BLACK, F_SMALL)))
            y += 100

        clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.VIDEORESIZE:
                W = max(MIN_W, e.w); H = max(MIN_H, e.h)
                init_window(W, H)
                return links_screen()
            r = link_in.handle(e)
            if r is not None and r:
                kind, val = parse_link(r)
                if kind == "level":
                    net_download(val)
                    msg = f"Загрузка уровня {val}..."; msg_t = 60
                    link_in.text = ""
                elif kind == "user":
                    net_user_profile(val)
                    msg = f"Профиль {val}..."; msg_t = 60
                    link_in.text = ""
                else:
                    msg = "Неверная ссылка"; msg_t = 120
                    link_in.text = ""
            if go_btn.handle(e):
                kind, val = parse_link(link_in.text)
                if kind == "level":
                    net_download(val)
                    msg = f"Загрузка уровня {val}..."; msg_t = 60
                    link_in.text = ""
                elif kind == "user":
                    net_user_profile(val)
                    msg = f"Профиль {val}..."; msg_t = 60
                    link_in.text = ""
                else:
                    msg = "Неверная ссылка"; msg_t = 120
            if back.handle(e):
                return "menu"
            if refresh.handle(e):
                if tab == "levels": net_featured()
                elif tab == "top": net_top()
                else: net_users()
                msg = "Обновление..."; msg_t = 60
            if tab_lvl.handle(e):
                tab = "levels"; scroll = 0; net_featured()
            if tab_top.handle(e):
                tab = "top"; scroll = 0; net_top()
            if tab_usr.handle(e):
                tab = "users"; scroll = 0; net_users()
            if e.type == pygame.MOUSEWHEEL:
                scroll = max(0, min(max(0, len(items) * 100 - (H - 320)), scroll - e.y * 40))
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return "menu"
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my_pos = e.pos
                for idx, b in rows:
                    if b.rect.collidepoint(mx, my_pos):
                        item = items[idx]
                        if tab == "users":
                            net_user_profile(item.get("username"))
                            msg = "Профиль..."; msg_t = 60
                        else:
                            net_download(item.get("code"))
                            msg = "Загрузка уровня..."; msg_t = 60
                y2 = 220 - scroll
                for i in range(len(items)):
                    if pygame.Rect(100, y2, W - 340, 90).collidepoint(mx, my_pos):
                        item = items[i]
                        if tab == "users":
                            net_user_profile(item.get("username"))
                            msg = "Профиль..."; msg_t = 60
                        else:
                            net_download(item.get("code"))
                            msg = "Загрузка уровня..."; msg_t = 60
                    y2 += 100

        if NET["done"] and NET["label"] == "featured":
            if NET["result"] is not None:
                items = NET["result"] if isinstance(NET["result"], list) else []
                NET["result"] = None
            elif NET["error"]:
                msg = f"Ошибка: {NET['error']}"; msg_t = 120
                NET["error"] = None
        if NET["done"] and NET["label"] == "top":
            if NET["result"] is not None:
                items = NET["result"] if isinstance(NET["result"], list) else []
                NET["result"] = None
            elif NET["error"]:
                msg = f"Ошибка: {NET['error']}"; msg_t = 120
                NET["error"] = None
        if NET["done"] and NET["label"] == "users":
            if NET["result"] is not None:
                items = NET["result"] if isinstance(NET["result"], list) else []
                NET["result"] = None
            elif NET["error"]:
                msg = f"Ошибка: {NET['error']}"; msg_t = 120
                NET["error"] = None
        if NET["done"] and NET["label"] == "profile" and NET["result"] is not None:
            return ("profile", NET["result"])
        if NET["done"] and NET["label"] == "download" and NET["result"] is not None:
            s = sanitize_level(NET["result"], "С сервера")
            if s:
                code = s.get("code")
                replaced = False
                if code:
                    for i, u in enumerate(USER_LEVELS):
                        if u.get("code") == code:
                            USER_LEVELS[i] = s
                            replaced = True
                            break
                if not replaced:
                    USER_LEVELS.append(s)
                save_user_levels(USER_LEVELS)
                msg = "Уровень добавлен!"
            else:
                msg = "Неверный ответ сервера"
            msg_t = 200
            NET["result"] = None
            NET["error"] = None
        elif NET["done"] and NET["label"] == "download" and NET["error"]:
            msg = f"Ошибка: {NET['error']}"; msg_t = 180
            NET["error"] = None

        if msg_t > 0:
            msg_t -= 1

        bg(screen, pygame.time.get_ticks() / 1000)
        t = F_BIG.render("ССЫЛКИ", True, WHITE)
        screen.blit(t, (W // 2 - t.get_width() // 2, 30))
        sub = F_TINY.render(f"{SERVER_URL}", True, (180, 190, 220))
        screen.blit(sub, (W // 2 - sub.get_width() // 2, 88))
        link_in.draw(screen)
        go_btn.draw(screen)
        tab_lvl.draw(screen)
        tab_top.draw(screen)
        tab_usr.draw(screen)
        if tab == "levels": active_rect = tab_lvl.rect
        elif tab == "top": active_rect = tab_top.rect
        else: active_rect = tab_usr.rect
        pygame.draw.rect(screen, WHITE, active_rect.inflate(8, 8), 3, border_radius=12)

        mx, my_pos = pygame.mouse.get_pos()
        y = 220 - scroll
        for i, item in enumerate(items):
            r = pygame.Rect(100, y, W - 340, 90)
            if r.bottom > 180 and r.top < H - 100:
                hover = r.collidepoint(mx, my_pos)
                pygame.draw.rect(screen, (55, 60, 95) if hover else (35, 40, 68),
                                 r, border_radius=14)
                pygame.draw.rect(screen, ACCENT if hover else LIGHT, r, 3, border_radius=14)
                if tab in ("levels", "top"):
                    code = item.get("code", "?")
                    name = item.get("name", "?")
                    diff = item.get("difficulty", "Normal")
                    author = item.get("author", "guest")
                    obj = item.get("objects", 0)
                    skin = item.get("skin", "default")
                    rating = item.get("rating", 0)
                    num = F_BIG.render(code, True, GOLD)
                    screen.blit(num, (r.x + 20, r.centery - num.get_height() // 2))
                    nm = F_MED.render(name, True, WHITE)
                    screen.blit(nm, (r.x + 180, r.y + 10))
                    dc = {"Easy": GREEN, "Normal": GOLD, "Hard": ORANGE, "Insane": RED}.get(diff, WHITE)
                    screen.blit(F_SMALL.render(f"{diff}  ·  объекты: {obj}", True, dc),
                                (r.x + 180, r.y + 40))
                    draw_stars(screen, r.x + 180, r.y + 68, rating, size=14)
                    draw_skin_dot(screen, r.right - 200, r.y + 65, 8, skin,
                                  pygame.time.get_ticks() / 1000)
                    screen.blit(F_SMALL.render(f"@{author}", True, GOLD),
                                (r.right - 180, r.y + 57))
                else:
                    uname = item.get("username", "?")
                    cnt = item.get("levels", 0)
                    skin = item.get("skin", "default")
                    draw_skin_dot(screen, r.x + 30, r.centery, 12, skin,
                                  pygame.time.get_ticks() / 1000)
                    nm = F_MED.render(f"@{uname}", True, GOLD)
                    screen.blit(nm, (r.x + 60, r.centery - nm.get_height() // 2))
                    screen.blit(F_SMALL.render(f"уровней: {cnt}", True, (200, 210, 230)),
                                (r.x + 300, r.centery - 8))
            y += 100

        if not items:
            empty = F_MED.render("Пусто. Нажми ОБНОВИТЬ или вставь ссылку.",
                                 True, (160, 170, 200))
            screen.blit(empty, (W // 2 - empty.get_width() // 2, H // 2 + 20))
        for _, b in rows:
            b.draw(screen)
        back.draw(screen)
        refresh.draw(screen)

        if msg_t > 0:
            mt = F_SMALL.render(msg, True, GREEN)
            rr = pygame.Rect(W // 2 - mt.get_width() // 2 - 20, H - 130,
                             mt.get_width() + 40, 42)
            pygame.draw.rect(screen, DARK, rr, border_radius=10)
            pygame.draw.rect(screen, GREEN, rr, 2, border_radius=10)
            screen.blit(mt, (W // 2 - mt.get_width() // 2, H - 122))

        draw_account_badge(screen)
        pygame.display.flip()


def user_profile_screen(profile):
    global W, H, screen, USER_LEVELS
    uname = profile.get("username", "?")
    levels = profile.get("levels", [])
    skin = profile.get("skin", "default")
    scroll = 0
    msg = ""
    msg_t = 0

    while True:
        back = Btn((20, H - 70, 150, 50), "← НАЗАД", GRAY, WHITE, F_SMALL)
        copy_app = Btn((W - 260, H - 70, 240, 50), "ССЫЛКА В ИГРУ", ACCENT2, BLACK, F_SMALL)
        copy_web = Btn((W - 510, H - 70, 240, 50), "ССЫЛКА НА САЙТ", GOLD, BLACK, F_SMALL)

        rows = []
        y = 220 - scroll
        for i in range(len(levels)):
            rows.append((i, Btn((W - 200, y + 22, 130, 46), "ИГРАТЬ",
                                ACCENT, BLACK, F_SMALL)))
            y += 100

        clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.VIDEORESIZE:
                W = max(MIN_W, e.w); H = max(MIN_H, e.h)
                init_window(W, H)
                return user_profile_screen(profile)
            if back.handle(e):
                return "menu"
            if copy_app.handle(e):
                link = make_share_link("user", uname)
                msg = f"Скопировано: {link}" if copy_to_clipboard(link) else link
                msg_t = 180
            if copy_web.handle(e):
                url = make_web_link("user", uname)
                msg = f"Скопировано: {url}" if copy_to_clipboard(url) else url
                msg_t = 200
            if e.type == pygame.MOUSEWHEEL:
                scroll = max(0, min(max(0, len(levels) * 100 - (H - 320)), scroll - e.y * 40))
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return "menu"
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my_pos = e.pos
                for idx, b in rows:
                    if b.rect.collidepoint(mx, my_pos):
                        code = levels[idx].get("code")
                        if code:
                            net_download(code)
                            msg = "Загрузка уровня..."; msg_t = 60
                y2 = 220 - scroll
                for i in range(len(levels)):
                    if pygame.Rect(100, y2, W - 340, 90).collidepoint(mx, my_pos):
                        code = levels[i].get("code")
                        if code:
                            net_download(code)
                            msg = "Загрузка уровня..."; msg_t = 60
                    y2 += 100

        if NET["done"] and NET["label"] == "download" and NET["result"] is not None:
            s = sanitize_level(NET["result"], "С сервера")
            if s:
                code = s.get("code")
                replaced = False
                if code:
                    for i, u in enumerate(USER_LEVELS):
                        if u.get("code") == code:
                            USER_LEVELS[i] = s
                            replaced = True
                            break
                if not replaced:
                    USER_LEVELS.append(s)
                save_user_levels(USER_LEVELS)
                msg = "Уровень добавлен!"
            else:
                msg = "Неверный ответ сервера"
            msg_t = 200
            NET["result"] = None
            NET["error"] = None
        elif NET["done"] and NET["label"] == "download" and NET["error"]:
            msg = f"Ошибка: {NET['error']}"; msg_t = 180
            NET["error"] = None
        if msg_t > 0:
            msg_t -= 1

        bg(screen, pygame.time.get_ticks() / 1000)
        draw_skin_dot(screen, W // 2 - 140, 60, 25, skin, pygame.time.get_ticks() / 1000)
        t = F_BIG.render(f"@{uname}", True, GOLD)
        screen.blit(t, (W // 2 - 90, 30))
        info = F_SMALL.render(f"Уровней: {len(levels)}  ·  Скин: {SKINS.get(skin, SKINS['default'])['name']}",
                              True, (200, 210, 230))
        screen.blit(info, (W // 2 - info.get_width() // 2, 90))
        linktxt = F_TINY.render(make_share_link("user", uname) + "  ·  " + make_web_link("user", uname),
                                True, (160, 170, 200))
        screen.blit(linktxt, (W // 2 - linktxt.get_width() // 2, 118))

        mx, my_pos = pygame.mouse.get_pos()
        y = 220 - scroll
        for i, item in enumerate(levels):
            r = pygame.Rect(100, y, W - 340, 90)
            if r.bottom > 160 and r.top < H - 100:
                hover = r.collidepoint(mx, my_pos)
                pygame.draw.rect(screen, (55, 60, 95) if hover else (35, 40, 68),
                                 r, border_radius=14)
                pygame.draw.rect(screen, ACCENT if hover else LIGHT, r, 3, border_radius=14)
                code = item.get("code", "?")
                nm = item.get("name", "?")
                diff = item.get("difficulty", "Normal")
                rating = item.get("rating", 0)
                num = F_BIG.render(code, True, GOLD)
                screen.blit(num, (r.x + 20, r.centery - num.get_height() // 2))
                screen.blit(F_MED.render(nm, True, WHITE), (r.x + 180, r.y + 15))
                dc = {"Easy": GREEN, "Normal": GOLD, "Hard": ORANGE, "Insane": RED}.get(diff, WHITE)
                screen.blit(F_SMALL.render(diff, True, dc), (r.x + 180, r.y + 42))
                draw_stars(screen, r.x + 180, r.y + 65, rating, size=14)
            y += 100

        if not levels:
            empty = F_MED.render("Пользователь ещё не выложил уровней.",
                                 True, (160, 170, 200))
            screen.blit(empty, (W // 2 - empty.get_width() // 2, H // 2))
        for _, b in rows:
            b.draw(screen)
        back.draw(screen)
        copy_app.draw(screen)
        copy_web.draw(screen)
        if msg_t > 0:
            mt = F_SMALL.render(msg, True, GREEN)
            rr = pygame.Rect(W // 2 - mt.get_width() // 2 - 20, H - 130,
                             mt.get_width() + 40, 42)
            pygame.draw.rect(screen, DARK, rr, border_radius=10)
            pygame.draw.rect(screen, GREEN, rr, 2, border_radius=10)
            screen.blit(mt, (W // 2 - mt.get_width() // 2, H - 122))
        draw_account_badge(screen)
        pygame.display.flip()


def play_level(data, idx, levels):
    global W, H, screen, LANES
    lane = 1
    ty = LANES[1]
    py = LANES[1]
    px = 200
    cam = 0
    coins = 0
    total_coins = sum(1 for o in data["obstacles"] if o["type"] == "coin")
    spd = 1.0
    parts = []
    trail = []
    state = "playing"
    hit = set()
    finish = data["length"]
    rate_msg = ""
    rate_msg_t = 0
    rate_done = False

    def spawn(x, y, c, n=14):
        for _ in range(n):
            parts.append({"x": x, "y": y,
                          "vx": (pygame.time.get_ticks() % 100 - 50) / 20,
                          "vy": -(pygame.time.get_ticks() % 100) / 25 - 1,
                          "life": 30, "color": c})

    is_rater = (ACCOUNT["username"] == RATING_USER)

    while True:
        clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.VIDEORESIZE:
                W = max(MIN_W, e.w); H = max(MIN_H, e.h)
                init_window(W, H)
                return ("resize", None)
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return ("menu", None)
                if state != "playing":
                    if e.key == pygame.K_r:
                        return ("replay", idx)
                    if e.key == pygame.K_RETURN and state == "win":
                        if idx + 1 < len(levels):
                            return ("next", idx + 1)
                        return ("menu", None)
                    if state == "win" and is_rater and data.get("code"):
                        if pygame.K_1 <= e.key <= pygame.K_5 and not rate_done:
                            stars = e.key - pygame.K_0
                            net_rate(data["code"], stars)
                            rate_msg = f"Ставим {stars}★..."; rate_msg_t = 60
                else:
                    if e.key in (pygame.K_UP, pygame.K_w) and lane > 0:
                        lane -= 1; ty = LANES[lane]
                    if e.key in (pygame.K_DOWN, pygame.K_s) and lane < 2:
                        lane += 1; ty = LANES[lane]

        py += (ty - py) * 0.28
        py = max(LANES[0], min(LANES[2], py))

        if state == "playing":
            cam += SPEED * spd
            spd = max(1.0, spd - 0.002)
            pw = cam + px
            for i, o in enumerate(data["obstacles"]):
                if i in hit:
                    continue
                if abs(o["x"] - pw) < PS // 2 + 6:
                    if o["type"] in ("spike", "block") and o["lane"] == lane:
                        state = "dead"
                        spawn(px, py, RED, 25)
                    elif o["type"] == "coin" and o["lane"] == lane:
                        coins += 1; hit.add(i)
                        spawn(px, py, GOLD, 12)
                    elif o["type"] == "jump" and o["lane"] == lane:
                        hit.add(i); spawn(px, py, GREEN, 14)
                    elif o["type"] == "speed" and o["lane"] == lane:
                        hit.add(i); spd = 1.5
                        spawn(px, py, ACCENT2, 14)
            if cam + px >= finish:
                state = "win"
                spawn(px, py, GREEN, 30)

        trail.append((px, py))
        if len(trail) > 12:
            trail.pop(0)
        for p in parts[:]:
            p["x"] += p["vx"]; p["y"] += p["vy"]; p["vy"] += 0.3
            p["life"] -= 1
            if p["life"] <= 0:
                parts.remove(p)

        if NET["done"] and NET["label"] == "rate":
            if NET["result"] and NET["result"].get("rating"):
                data["rating"] = NET["result"]["rating"]
                rate_msg = f"Оценка: {NET['result']['rating']}★"
                rate_msg_t = 180
                rate_done = True
                NET["result"] = None
            elif NET["error"]:
                rate_msg = f"Ошибка: {NET['error']}"
                rate_msg_t = 180
                NET["error"] = None

        if rate_msg_t > 0:
            rate_msg_t -= 1

        bg(screen, pygame.time.get_ticks() / 1000, cam)
        for ly in LANES:
            pygame.draw.line(screen, (35, 50, 95), (0, ly + PS // 2 + 4), (W, ly + PS // 2 + 4), 2)

        prog = min(1.0, (cam + px) / finish)
        bw = W - 80
        pygame.draw.rect(screen, DARK, (40, 20, bw, 18), border_radius=9)
        pygame.draw.rect(screen, GREEN, (40, 20, int(bw * prog), 18), border_radius=9)
        pygame.draw.rect(screen, WHITE, (40, 20, bw, 18), 2, border_radius=9)

        fx = finish - cam
        if -100 < fx < W + 100:
            pygame.draw.rect(screen, GREEN, (fx, LANES[0] - 40, 20, LANES[2] - LANES[0] + 100), border_radius=6)
            pygame.draw.rect(screen, WHITE, (fx, LANES[0] - 40, 20, LANES[2] - LANES[0] + 100), 3, border_radius=6)
            t = F_SMALL.render("FINISH", True, WHITE)
            screen.blit(t, (fx - 20, LANES[0] - 70))

        for i, o in enumerate(data["obstacles"]):
            ox = o["x"] - cam
            if ox < -80 or ox > W + 80:
                continue
            if o["type"] == "coin" and i in hit:
                continue
            if o["type"] in ("jump", "speed") and i in hit:
                continue
            draw_obj(screen, ox, LANES[o["lane"]], o["type"])

        body, border = get_skin_colors(CURRENT_SKIN, pygame.time.get_ticks() / 1000)
        for i, (tx, tyy) in enumerate(trail):
            a = (i + 1) / len(trail)
            r = max(2, int(PS / 2 * a))
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*body, int(150 * a)), (r, r), r)
            screen.blit(s, (tx - r, tyy - r))

        if state != "dead":
            pr = pygame.Rect(px - PS // 2, py - PS // 2, PS, PS)
            pygame.draw.rect(screen, body, pr, border_radius=8)
            pygame.draw.rect(screen, border, pr, 3, border_radius=8)
            pygame.draw.circle(screen, DARK, (pr.x + 12, pr.y + 14), 3)
            pygame.draw.circle(screen, DARK, (pr.x + 28, pr.y + 14), 3)

        for p in parts:
            a = max(0.0, p["life"] / 30)
            r = max(1, int(4 * a))
            pygame.draw.circle(screen, p["color"], (int(p["x"]), int(p["y"])), r)

        t = F_MED.render(f"{idx + 1}. {data['name']}", True, WHITE)
        screen.blit(t, (20, 60))
        dc = {"Easy": GREEN, "Normal": GOLD, "Hard": ORANGE, "Insane": RED}.get(
            data.get("difficulty", "Normal"), WHITE)
        screen.blit(F_SMALL.render(data.get("difficulty", "Normal"), True, dc), (20, 92))
        if data.get("author"):
            draw_skin_dot(screen, 30, 128, 8, data.get("authorSkin", "default"),
                          pygame.time.get_ticks() / 1000)
            screen.blit(F_SMALL.render(f"@{data['author']}", True, GOLD), (46, 118))
        screen.blit(F_MED.render(f"Монеты: {coins}/{total_coins}", True, GOLD), (W - 220, 60))
        hint = F_TINY.render("W/S или ↑/↓ — дорожка | ESC — меню", True, (180, 190, 220))
        screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 26))

        if state == "dead":
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 170)); screen.blit(ov, (0, 0))
            t = F_HUGE.render("GAME OVER", True, RED)
            screen.blit(t, (W // 2 - t.get_width() // 2, H // 2 - 90))
            t2 = F_MED.render("R — заново   ESC — в меню", True, WHITE)
            screen.blit(t2, (W // 2 - t2.get_width() // 2, H // 2 + 10))

        if state == "win":
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 160)); screen.blit(ov, (0, 0))
            t = F_HUGE.render("ПОБЕДА!", True, GREEN)
            screen.blit(t, (W // 2 - t.get_width() // 2, H // 2 - 140))
            t2 = F_MED.render(f"Монеты: {coins}/{total_coins}", True, GOLD)
            screen.blit(t2, (W // 2 - t2.get_width() // 2, H // 2 - 50))

            if is_rater and data.get("code"):
                ratetxt = F_MED.render("Поставь оценку (1-5):", True, GOLD)
                screen.blit(ratetxt, (W // 2 - ratetxt.get_width() // 2, H // 2 + 5))
                bw_star = 60
                bx = W // 2 - (5 * (bw_star + 5)) // 2
                by = H // 2 + 45
                current = data.get("rating", 0)
                mx, my_pos = pygame.mouse.get_pos()
                for i in range(5):
                    r = pygame.Rect(bx + i * (bw_star + 5), by, bw_star, bw_star)
                    hover = r.collidepoint(mx, my_pos)
                    col = (GOLD if i < current else (60, 60, 80))
                    if hover:
                        col = tuple(min(255, x + 40) for x in col)
                    pygame.draw.rect(screen, col, r, border_radius=8)
                    pygame.draw.rect(screen, WHITE, r, 2, border_radius=8)
                    t3 = F_MED.render(str(i + 1), True,
                                      BLACK if hover or i < current else WHITE)
                    screen.blit(t3, (r.centerx - t3.get_width() // 2,
                                     r.centery - t3.get_height() // 2))

            t3 = F_SMALL.render("R — заново   ENTER — дальше   ESC — меню", True, WHITE)
            screen.blit(t3, (W // 2 - t3.get_width() // 2, H // 2 + 130))

        if rate_msg_t > 0:
            mt = F_SMALL.render(rate_msg, True, GOLD)
            rr = pygame.Rect(W // 2 - mt.get_width() // 2 - 15, H - 60,
                             mt.get_width() + 30, 32)
            pygame.draw.rect(screen, DARK, rr, border_radius=8)
            pygame.draw.rect(screen, GOLD, rr, 2, border_radius=8)
            screen.blit(mt, (W // 2 - mt.get_width() // 2, H - 54))

        pygame.display.flip()


def editor():
    global W, H, screen, USER_LEVELS
    builtin = load_levels()
    USER_LEVELS = load_user_levels()
    target = "builtin"
    idx = 0
    tool = "spike"
    scroll = 0
    msg = ""
    msg_t = 0
    rename_in = None

    def pos_to_lane(my):
        if my < 90 or my > H - 60:
            return None
        best, bd = None, 100
        for i, ly in enumerate(LANES):
            d = abs(my - ly)
            if d < bd:
                bd = d; best = i
        return best

    while True:
        tools = [("spike", "ШИП", RED), ("block", "БЛОК", PURPLE),
                 ("coin", "МОНЕТА", GOLD), ("jump", "УСКОРИТ.", GREEN),
                 ("speed", "ЗАМЕДЛ.", ACCENT2), ("finish", "ФИНИШ", GREEN)]
        tool_btns = []
        y = 200
        for key, label, col in tools:
            tool_btns.append((key, Btn((20, y, 150, 42), label, col, BLACK, F_SMALL)))
            y += 50

        back = Btn((W - 170, 20, 150, 45), "← МЕНЮ", GRAY, WHITE, F_SMALL)
        save = Btn((W - 340, 20, 160, 45), "СОХРАНИТЬ", GREEN, BLACK, F_SMALL)
        exp = Btn((W - 520, 20, 170, 45), "ЭКСПОРТ", ACCENT, BLACK, F_SMALL)
        imp = Btn((W - 700, 20, 170, 45), "ИМПОРТ", ORANGE, BLACK, F_SMALL)
        srv = Btn((W - 880, 20, 170, 45), "НА СЕРВЕР", ACCENT2, BLACK, F_SMALL)
        ren = Btn((W - 1060, 20, 170, 45), "ПЕРЕИМЕНОВАТЬ", GOLD, BLACK, F_TINY)
        new_builtin = Btn((20, 20, 150, 45), "+ ВСТРОЕННЫЙ", GOLD, BLACK, F_TINY)
        new_user = Btn((180, 20, 150, 45), "+ МОЙ", GREEN, BLACK, F_TINY)
        tab_b = Btn((20, 130, 70, 42), "◀", GRAY, WHITE, F_SMALL)
        tab_n = Btn((100, 130, 70, 42), "▶", GRAY, WHITE, F_SMALL)

        def current_list():
            return builtin if target == "builtin" else USER_LEVELS

        def save_current():
            if target == "builtin":
                save_levels(builtin)
            else:
                save_user_levels(USER_LEVELS)

        def do_import():
            nonlocal idx, msg, msg_t
            nl, text = import_dialog()
            if nl:
                if target == "user":
                    USER_LEVELS.extend(nl); save_user_levels(USER_LEVELS)
                else:
                    builtin.extend(nl); save_levels(builtin)
                idx = len(current_list()) - len(nl)
                msg = text + " (сохранено)"; msg_t = 150
            else:
                msg = text; msg_t = 120

        def do_rename(new_name):
            nonlocal msg, msg_t
            lvl_ref = current_list()[idx]
            if not lvl_ref.get("code"):
                lvl_ref["name"] = new_name
                save_current()
                msg = "Переименовано локально"
                msg_t = 200
                return
            if ACCOUNT["username"] != lvl_ref.get("author"):
                msg = "Это не ваш уровень"
                msg_t = 180
                return
            net_rename(lvl_ref["code"], new_name)
            msg = "Переименование..."; msg_t = 60

        lst = current_list()
        if not lst:
            lst.append(mk("Новый", "Normal", [], 5000))
        if idx >= len(lst):
            idx = 0
        lvl = lst[idx]

        clock.tick(FPS)
        resize_break = False
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.VIDEORESIZE:
                W = max(MIN_W, e.w); H = max(MIN_H, e.h)
                init_window(W, H); resize_break = True; break

            if rename_in is not None:
                res = rename_in.handle(e)
                if res is not None:
                    if res.strip():
                        do_rename(res.strip())
                    rename_in = None
                    continue
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    rename_in = None
                    continue
                if e.type == pygame.MOUSEBUTTONDOWN and not rename_in.rect.collidepoint(e.pos):
                    rename_in = None
                continue

            for key, b in tool_btns:
                if b.handle(e):
                    tool = key
            if back.handle(e): return "menu"
            if save.handle(e): save_current(); msg = "Сохранено!"; msg_t = 90
            if exp.handle(e):
                fn = f"exported_{lvl['name'].replace(' ', '_')}.json"
                with open(fn, "w", encoding="utf-8") as f:
                    json.dump(lvl, f, ensure_ascii=False, indent=2)
                msg = f"Экспорт: {fn}"; msg_t = 120
            if imp.handle(e): do_import()
            if srv.handle(e) and NET["done"]:
                net_upload(lvl); msg = "Загрузка на сервер..."; msg_t = 60
            if ren.handle(e):
                if not lvl.get("code"):
                    msg = "Сначала залей на сервер"; msg_t = 180
                elif ACCOUNT["username"] != lvl.get("author"):
                    msg = "Это не ваш уровень"; msg_t = 180
                else:
                    rename_in = TextInput((W // 2 - 300, H // 2 - 30, 600, 60),
                                          "новое имя", initial=lvl["name"])
            if new_builtin.handle(e):
                builtin.append(mk(f"Уровень {len(builtin)+1}", "Normal", [], 5000))
                target = "builtin"; idx = len(builtin) - 1
            if new_user.handle(e):
                USER_LEVELS.append(mk(f"Мой {len(USER_LEVELS)+1}", "Normal", [], 5000))
                target = "user"; idx = len(USER_LEVELS) - 1
            if tab_b.handle(e) or tab_n.handle(e):
                target = "builtin" if target == "user" else "user"
                idx = 0; scroll = 0
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: return "menu"
                if e.key == pygame.K_s: save_current(); msg = "Сохранено!"; msg_t = 90
                if e.key == pygame.K_e:
                    fn = f"exported_{lvl['name'].replace(' ', '_')}.json"
                    with open(fn, "w", encoding="utf-8") as f:
                        json.dump(lvl, f, ensure_ascii=False, indent=2)
                    msg = f"Экспорт: {fn}"; msg_t = 120
                if e.key == pygame.K_i: do_import()
                if e.key == pygame.K_u and NET["done"]:
                    net_upload(lvl); msg = "Загрузка на сервер..."; msg_t = 60
                if e.key == pygame.K_n:
                    if lvl.get("code") and ACCOUNT["username"] == lvl.get("author"):
                        rename_in = TextInput((W // 2 - 300, H // 2 - 30, 600, 60),
                                              "новое имя", initial=lvl["name"])
                    else:
                        msg = "Переименовать можно только свои залитые уровни"
                        msg_t = 200
                if e.key == pygame.K_a: scroll = max(0, scroll - 60)
                if e.key == pygame.K_d: scroll += 60
                if e.key == pygame.K_TAB:
                    target = "builtin" if target == "user" else "user"
                    idx = 0; scroll = 0
            if e.type == pygame.MOUSEWHEEL:
                scroll = max(0, scroll - e.y * 50)
            if e.type == pygame.MOUSEBUTTONDOWN and e.pos[0] > 190 and e.pos[1] > 80:
                mx, my = e.pos
                if tool == "finish":
                    if e.button == 1:
                        lvl["length"] = int(mx + scroll)
                else:
                    lane = pos_to_lane(my)
                    if lane is not None:
                        wx = int(mx + scroll)
                        if e.button == 1:
                            lvl["obstacles"].append({"x": wx, "lane": lane, "type": tool})
                        elif e.button == 3:
                            for i, o in enumerate(lvl["obstacles"]):
                                if o["lane"] == lane and abs(o["x"] - wx) < 40:
                                    lvl["obstacles"].pop(i); break

        if resize_break: continue

        if NET["done"] and NET["label"] == "upload":
            if NET["result"]:
                code = NET["result"].get("code")
                if code:
                    msg = f"Код: {code}  ·  {make_share_link('level', code)}"
                    copy_lvl = dict(lvl)
                    copy_lvl["code"] = code
                    if ACCOUNT["username"]:
                        copy_lvl["author"] = ACCOUNT["username"]
                        copy_lvl["authorSkin"] = CURRENT_SKIN
                    if not any(u.get("code") == code for u in USER_LEVELS):
                        USER_LEVELS.append(copy_lvl)
                        save_user_levels(USER_LEVELS)
                else:
                    msg = "Загружено!"
                msg_t = 400 if code else 200
                NET["result"] = None
            elif NET["error"]:
                msg = f"Ошибка: {NET['error']}"
                msg_t = 180
                NET["error"] = None

        if NET["done"] and NET["label"] == "rename":
            if NET["result"] and NET["result"].get("name"):
                if idx < len(current_list()):
                    current_list()[idx]["name"] = NET["result"]["name"]
                    save_current()
                msg = f"Переименовано: {NET['result']['name']}"
                msg_t = 240
                NET["result"] = None
            elif NET["error"]:
                msg = f"Ошибка: {NET['error']}"
                msg_t = 180
                NET["error"] = None

        if msg_t > 0: msg_t -= 1

        bg(screen, pygame.time.get_ticks() / 1000, scroll)
        for ly in LANES:
            pygame.draw.line(screen, (35, 50, 95), (0, ly + PS // 2 + 4), (W, ly + PS // 2 + 4), 2)
        for o in lvl["obstacles"]:
            ox = o["x"] - scroll
            if -60 < ox < W + 60:
                draw_obj(screen, ox, LANES[o["lane"]], o["type"])
        fx = lvl["length"] - scroll
        if -50 < fx < W + 50:
            pygame.draw.rect(screen, GREEN, (fx, LANES[0] - 40, 20, LANES[2] - LANES[0] + 100), border_radius=6)
            pygame.draw.rect(screen, WHITE, (fx, LANES[0] - 40, 20, LANES[2] - LANES[0] + 100), 2, border_radius=6)
            t = F_TINY.render("FINISH", True, WHITE)
            screen.blit(t, (fx - 15, LANES[0] - 62))

        panel = pygame.Surface((190, H), pygame.SRCALPHA)
        panel.fill((10, 12, 24, 215)); screen.blit(panel, (0, 0))
        pygame.draw.line(screen, ACCENT, (190, 0), (190, H), 2)
        t = F_MED.render("ИНСТРУМЕНТЫ", True, WHITE); screen.blit(t, (30, 90))
        t2 = F_TINY.render("ЛКМ — поставить | ПКМ — удалить", True, (170, 180, 210))
        screen.blit(t2, (15, H - 40))
        for key, b in tool_btns:
            b.draw(screen)
            if key == tool:
                pygame.draw.rect(screen, WHITE, b.rect.inflate(6, 6), 3, border_radius=10)
        tab_b.draw(screen); tab_n.draw(screen)

        top = pygame.Surface((W, 80), pygame.SRCALPHA)
        top.fill((10, 12, 24, 200)); screen.blit(top, (0, 0))
        cur_label = "ВСТРОЕННЫЕ" if target == "builtin" else "МОИ"
        t = F_MED.render(f"[{cur_label}] {idx+1}/{len(lst)}: {lvl['name']}", True, WHITE)
        screen.blit(t, (420, 25))

        back.draw(screen); save.draw(screen); exp.draw(screen)
        imp.draw(screen); srv.draw(screen); ren.draw(screen)
        new_builtin.draw(screen); new_user.draw(screen)

        hint = F_TINY.render("A/D — прокрутка | TAB — вкладка | S — сохранить | E — экспорт | I — импорт | U — на сервер | N — переименовать",
                             True, (170, 180, 210))
        screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 22))

        if rename_in is not None:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 180)); screen.blit(ov, (0, 0))
            t = F_MED.render("Новое имя уровня:", True, WHITE)
            screen.blit(t, (W // 2 - t.get_width() // 2, H // 2 - 80))
            rename_in.draw(screen)
            t2 = F_TINY.render("ENTER — сохранить | ESC — отмена", True, (200, 200, 220))
            screen.blit(t2, (W // 2 - t2.get_width() // 2, H // 2 + 50))

        if msg_t > 0:
            mt = F_MED.render(msg, True, GREEN)
            rr = pygame.Rect(W // 2 - mt.get_width() // 2 - 20, H - 100,
                             mt.get_width() + 40, 45)
            pygame.draw.rect(screen, DARK, rr, border_radius=10)
            pygame.draw.rect(screen, GREEN, rr, 2, border_radius=10)
            screen.blit(mt, (W // 2 - mt.get_width() // 2, H - 92))
        pygame.display.flip()


def open_donate_page():
    import webbrowser
    webbrowser.open("https://pay.cloudtips.ru/p/d8880b7d")


def main():
    init_window(DEFAULT_W, DEFAULT_H)
    load_account()
    while True:
        action = menu()
        if action == "quit":
            pygame.quit(); sys.exit()
        elif action == "sett":
            settings_screen()
        elif action == "acc":
            account_screen()
        elif action == "donate":
            open_donate_page()
        elif action == "links":
            r = links_screen()
            if isinstance(r, tuple) and r[0] == "profile":
                user_profile_screen(r[1])
        elif action == "play":
            while True:
                res = level_select("play")
                if res[0] == "back": break
                if res[0] == "profile":
                    user_profile_screen(res[1]); continue
                idx, src = res[1]
                levels = load_levels() if src == "builtin" else load_user_levels()
                if idx >= len(levels): continue
                inner = True
                while inner:
                    r = play_level(levels[idx], idx, levels)
                    if r[0] == "replay": continue
                    elif r[0] == "next": idx = r[1]; continue
                    elif r[0] == "resize": break
                    else: inner = False
                break
        elif action == "edit":
            editor()


if __name__ == "__main__":
    main()