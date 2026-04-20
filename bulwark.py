#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itertools
import json
import logging
import os
import queue
import random
import sys
import threading
import time
import argparse
from collections import deque
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path
from typing import Callable, Deque, Dict, Iterator, List, Optional

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry as _Retry
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

def _need_requests():
    if not _REQUESTS_OK:
        print("  pip install requests")
        raise SystemExit(1)


def _data_dir() -> Path:
    root = os.getenv("LOCALAPPDATA") or str(Path.home()) if os.name == "nt" else str(Path.home())
    d = Path(root) / "bwk"
    d.mkdir(parents=True, exist_ok=True)
    return d

BASE      = _data_dir()
CFG_FILE  = str(BASE / "config.json")
PROG_FILE = str(BASE / "progress.txt")
LOG_FILE  = str(BASE / "bulwark.log")
FREE_DEF  = str(BASE / "free.txt")
TGTS_DEF  = str(BASE / "targets.txt")

VERSION      = "2.5.3"
DISCORD_LINK = "discord.gg/DunjgWSNG8"
QUOTE        = "il n'y a qu'un argument contre le suicide : le temps."

NON_INTERACTIVE = False
RESUME_POLICY   = "ask"

ALPHABET      = "abcdefghijklmnopqrstuvwxyz0123456789_."
ALPHA_ONLY    = "abcdefghijklmnopqrstuvwxyz"
ALPHA_DIG     = "abcdefghijklmnopqrstuvwxyz0123456789"
API_URL       = "https://discord.com/api/v9/users/@me/pomelo-attempt"
FLUSH_EVERY   = 50
JITTER        = (0.03, 0.22)
VALIDATOR_REV = "5"

VOWELS       = frozenset("aeiou")
RARE_LETTERS = frozenset("jkqvwxyz")

KEYBOARD_TRASH: set = {
    "qwe","wer","ert","rty","tyu","yui","uio","iop",
    "asd","sdf","dfg","fgh","ghj","hjk","jkl",
    "zxc","xcv","cvb","vbn","bnm",
    "qwer","wert","erty","rtyu","tyui","yuio","uiop",
    "asdf","sdfg","dfgh","fghj","ghjk","hjkl",
    "zxcv","xcvb","cvbn","vbnm",
    "123","234","345","456","567","678","789","890",
    "987","876","765","654","543","432","321",
    "1234","2345","3456","4567","5678","6789","7890",
    "9876","8765","7654","6543","5432","4321",
}

COMMON_3: set = {
    "the","and","for","are","but","not","you","all","can","her",
    "was","one","our","out","day","get","has","him","his","how",
    "man","new","now","old","see","two","way","who","boy","did",
    "its","let","put","say","she","too","use","dad","mom","bro",
    "sis","pro","god","lol","omg","wtf","brb","afk","irl","aka",
    "etc","fyi","tbh","imo","ngl","smh","rip","sus","npc","bot",
    "dev","mod","vip","ceo","api","run","win","try","fix","buy",
    "log","set","hit","map","key","tag","top","tip","end","big",
    "hot","bad","rad","raw","ace","age","ago","aid","aim","air",
    "ale","ant","ape","arc","arm","art","ash","ask","ate","awe",
    "axe","bay","bed","bid","bin","bit","bow","box","bug","bun",
    "bus","cab","cap","cat","cop","cot","cow","cry","cup","cut",
    "dog","dot","dry","dub","dug","duo","ear","eat","egg","elf",
    "elk","elm","emu","era","eve","ewe","eye","fan","fat","fax",
    "fee","few","fig","fit","fly","fog","fun","fur","gap","gas",
    "gem","gnu","gun","gut","guy","gym","ham","hat","hay","hen",
    "hex","hip","hop","hub","hug","hum","ice","ink","inn","ion",
    "ivy","jar","jaw","jay","jet","job","jot","joy","jug","jut",
    "keg","kid","kit","lab","lag","lap","law","lay","lea","lid",
    "lip","lit","lot","low","lug","mad","mar","mat","maw","med",
    "men","mid","mix","mob","mop","mud","mug","nap","net","nip",
    "nit","nod","nor","nun","nut","oak","oar","oat","odd","off",
    "oil","opt","orb","ore","owe","own","pad","pal","pan","paw",
    "pay","pea","peg","pen","pet","pie","pig","pin","pit","pod",
    "pop","pot","pow","pry","pub","pun","pup","rag","ram","ran",
    "rat","ray","ref","rep","rev","rib","rid","rim","rip","rob",
    "rod","roe","rot","row","rub","rug","rum","rut","sag","sap",
    "sat","saw","sax","sea","sew","sin","sip","sir","sit","ski",
    "sky","sly","sob","sod","son","sow","spa","spy","sty","sub",
    "sum","sun","tab","tan","tap","tar","tax","tea","ten","tie",
    "tin","toe","ton","tow","toy","tub","tug","van","vat","vet",
    "via","vim","vow","wag","war","wed","wig","wit","woe","wok",
    "won","woo","yak","yam","yap","yew","zap","zip","zoo",
}

COMMON_4: set = {
    "that","with","this","from","they","have","were","will","been",
    "said","when","time","like","just","your","some","what","come",
    "made","than","more","most","also","back","know","much","over",
    "such","only","even","well","make","good","look","year","work",
    "life","hand","down","here","live","play","real","free","cool",
    "want","give","take","keep","find","long","name","part","call",
    "next","both","same","show","form","help","land","last","late",
    "many","move","must","open","page","read","soon","stop","tell",
    "them","then","very","walk","ways","word","area","base","body",
    "book","case","city","door","face","fact","food","girl","goes",
    "gone","head","hold","home","hour","idea","into","kind","knew",
    "lady","left","line","list","love","main","mind","mine","near",
    "need","news","note","once","past","plan","plus","poor","rain",
    "rate","rest","rise","road","role","room","rule","runs","safe",
    "sale","save","says","self","sets","side","sign","size","sort",
    "step","term","test","text","thus","till","tips","told","tone",
    "took","town","true","turn","type","unit","used","view","wait",
    "warm","went","wide","wise","wish","wood","wore","worn","zero",
    "fire","dark","soul","star","moon","king","wolf","bear","lion",
    "hawk","blue","gold","void","null","data","code","hack","root",
    "game","race","fate","hate","mate","date","gate","wake","fake",
    "bake","cake","lake","rake","sake","tale","male","pale","cave",
    "gave","rave","wave","noob","nerd","geek","chad","simp","cope",
    "slay","grip","drip","flex","hype","dope","vibe","goat","yolo",
    "swag","rekt","giga","rizz","bruh","gang","clan","team","user",
    "pass","host","ping","buff","nerf","tank","heal","loot","raid",
    "boss","farm","push","rush","feed","tilt","dead","done","lost",
    "kill","wins","miss","fail","skip","hard","soft","fast","slow",
    "high","alex","adam","anna","jake","jane","john","kate","kyle",
    "liam","lily","lisa","luke","mark","maya","mike","nick","noah",
    "ryan","sara","zara","ruby","jade","rose","evan","emma","jack",
    "eric","1234","4321","6969","1337","0000","1111","2222","3333",
    "4444","5555","6666","7777","8888","9999","neon","nova","apex",
    "sync","flux","byte","bits","echo","grid","core","edge","loop",
    "node","peak","port","zone","mode","nest","pack","deck","rank",
    "stat",
}

_LEET: Dict[str, str] = {
    "0":"o","1":"i","2":"z","3":"e","4":"a","5":"s",
    "6":"g","7":"t","8":"b","9":"g",
}

def _deleet(s: str) -> str:
    return "".join(_LEET.get(c, c) for c in s)

DEFAULT_CFG: Dict = {
    "token":        "",
    "threads":      5,
    "rate":         1.8,
    "lengths":      [3, 4],
    "proxy":        None,
    "output":       FREE_DEF,
    "targets_file": TGTS_DEF,
    "webhooks":     [],
}


class _C:
    reset  = "\033[0m"
    bold   = "\033[1m"
    gray   = "\033[90m"
    green  = "\033[92m"
    yellow = "\033[93m"
    red    = "\033[91m"

def bold(s):   return f"{_C.bold}{s}{_C.reset}"
def gray(s):   return f"{_C.gray}{s}{_C.reset}"
def green(s):  return f"{_C.green}{s}{_C.reset}"
def yellow(s): return f"{_C.yellow}{s}{_C.reset}"
def red(s):    return f"{_C.red}{s}{_C.reset}"

W = 56

def _can_enc(s):
    try:
        s.encode(getattr(sys.stdout, "encoding", None) or "utf-8")
        return True
    except Exception:
        return False

H     = "─" if _can_enc("─") else "-"
ARROW = "→" if _can_enc("→") else "->"
SEP   = gray("  " + H * W)

LOGO = (
    "██████╗ ██╗   ██╗██╗     ██╗    ██╗ █████╗ ██████╗ ██╗  ██╗\n"
    "██╔══██╗██║   ██║██║     ██║    ██║██╔══██╗██╔══██╗██║ ██╔╝\n"
    "██████╔╝██║   ██║██║     ██║ █╗ ██║███████║██████╔╝█████╔╝ \n"
    "██╔══██╗██║   ██║██║     ██║███╗██║██╔══██║██╔══██╗██╔═██╗ \n"
    "██████╔╝╚██████╔╝███████╗╚███╔███╔╝██║  ██║██║  ██║██║  ██╗\n"
    "╚═════╝  ╚═════╝ ╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝"
) if _can_enc("█") else "BULWARK"


def _mk_logger():
    lg = logging.getLogger("bulwark")
    lg.setLevel(logging.DEBUG)
    if not lg.handlers:
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setFormatter(logging.Formatter(
            "%(asctime)s  [%(threadName)-8s]  %(levelname)-5s  %(message)s"
        ))
        lg.addHandler(fh)
    return lg

log = _mk_logger()


def load_cfg() -> Dict:
    if os.path.exists(CFG_FILE):
        try:
            with open(CFG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            m = {**DEFAULT_CFG, **data}
            if not Path(m["output"]).is_absolute():
                m["output"] = str(BASE / m["output"])
            if not Path(m["targets_file"]).is_absolute():
                m["targets_file"] = str(BASE / m["targets_file"])
            return m
        except Exception as e:
            log.warning(f"config error: {e}")
    return dict(DEFAULT_CFG)


def save_cfg(cfg: Dict):
    try:
        tmp = CFG_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        os.replace(tmp, CFG_FILE)
    except Exception as e:
        print(f"  config save failed: {e}")


def rp(p: str) -> str:
    try:
        path = Path(p)
        return str(path if path.is_absolute() else BASE / path)
    except Exception:
        return str(BASE / p)


def _cache_key(lengths: List[int], suffix: str = "") -> str:
    return f"v{VALIDATOR_REV}|{ALPHABET}|{','.join(str(x) for x in sorted(lengths))}{suffix}"


def combo_count_cached(cfg: Dict, lengths: List[int], suffix: str = "") -> int:
    cache = cfg.get("count_cache")
    if not isinstance(cache, dict):
        cache = {}
        cfg["count_cache"] = cache
    key = _cache_key(lengths, suffix)
    if isinstance(cache.get(key), int):
        return cache[key]
    n = _count_precision(lengths) if suffix == "|precision" else combo_count(lengths)
    cache[key] = n
    save_cfg(cfg)
    return n


_CHAR_RARITY: Dict[str, int] = {
    "a":1,"e":1,"t":1,"i":2,"o":2,"n":2,"s":2,"u":3,"r":3,"h":3,"l":3,"d":3,
    "c":4,"m":4,"g":4,"p":4,"b":5,"f":5,"w":5,"y":5,"k":7,"v":7,"j":8,"x":9,"q":10,"z":10,
    "0":2,"1":2,"2":2,"3":3,"4":3,"5":3,"6":3,"7":4,"8":4,"9":4,"_":1,".":1,
}

def _rarity(s: str) -> int:
    return sum(_CHAR_RARITY.get(c, 5) for c in s)


def is_valid(s: str) -> bool:
    if not s or len(s) < 3:
        return False
    if s[0] in "_." or s[-1] in "_.":
        return False
    if any(p in s for p in ("__", "..", "_.", "._")):
        return False
    if len(set(s)) == 1:
        return False
    if s in KEYBOARD_TRASH:
        return False
    if s.isdigit():
        return False
    if s == s[::-1]:
        return False
    if len(s) == 3 and s in COMMON_3:
        return False
    if len(s) == 4 and s in COMMON_4:
        return False
    if len(s) == 4 and s[0] == s[2] and s[1] == s[3] and s[0] != s[1]:
        return False
    if max(s.count(c) for c in set(s)) / len(s) > 0.6:
        return False
    alpha = set(c for c in s if c.isalpha())
    if len(alpha) == 1 and not s.isalpha():
        return False
    if s.isalpha() and alpha <= VOWELS:
        return False
    if s.isalpha():
        codes = [ord(c) for c in s]
        if all(codes[i+1] - codes[i] == 1 for i in range(len(codes)-1)):
            return False
        if all(codes[i] - codes[i+1] == 1 for i in range(len(codes)-1)):
            return False
    if any(c.isdigit() for c in s):
        plain = _deleet(s)
        if plain != s:
            if len(plain) == 3 and plain in COMMON_3:
                return False
            if len(plain) == 4 and plain in COMMON_4:
                return False
    return True


def _tier(s: str) -> int:
    has_spec  = "_" in s or "." in s
    has_digit = any(c.isdigit() for c in s)
    has_alpha = any(c.isalpha() for c in s)
    if has_spec:
        return 4
    if has_alpha and not has_digit:
        return 0 if len(s) == 3 else 1
    return 2 if len(s) == 3 else 3


def gen_tiered(lengths: List[int]) -> List[str]:
    buckets: Dict[int, List[str]] = {0: [], 1: [], 2: [], 3: [], 4: []}
    for n in sorted(lengths):
        for t in itertools.product(ALPHABET, repeat=n):
            s = "".join(t)
            if is_valid(s):
                buckets[_tier(s)].append(s)
    out: List[str] = []
    for k in sorted(buckets):
        out.extend(sorted(buckets[k], key=_rarity, reverse=True))
    return out


def gen_precision(lengths: List[int]) -> Iterator[str]:
    do_3 = 3 in lengths
    do_4 = 4 in lengths

    def _wave(pool: List[str]) -> Iterator[str]:
        pool.sort(key=_rarity, reverse=True)
        yield from pool

    if do_3:
        rare, common = [], []
        for t in itertools.product(ALPHA_ONLY, repeat=3):
            s = "".join(t)
            if not is_valid(s):
                continue
            (rare if any(c in RARE_LETTERS for c in s) else common).append(s)
        yield from _wave(rare)
        yield from _wave(common)

    if do_4:
        rare, common = [], []
        for t in itertools.product(ALPHA_DIG, repeat=4):
            s = "".join(t)
            if not is_valid(s):
                continue
            digits = sum(1 for c in s if c.isdigit())
            alpha  = [c for c in s if c.isalpha()]
            if not alpha or digits == 0 or digits > 2:
                continue
            (rare if any(c in RARE_LETTERS for c in alpha) else common).append(s)
        yield from _wave(rare)
        yield from _wave(common)

    if do_4:
        rare, common = [], []
        for t in itertools.product(ALPHA_ONLY, repeat=4):
            s = "".join(t)
            if not is_valid(s):
                continue
            (rare if any(c in RARE_LETTERS for c in s) else common).append(s)
        yield from _wave(rare)
        yield from _wave(common)


def _count_precision(lengths: List[int]) -> int:
    return sum(1 for _ in gen_precision(lengths))


def combo_count(lengths: List[int]) -> int:
    return sum(
        1 for n in lengths
        for t in itertools.product(ALPHABET, repeat=n)
        if is_valid("".join(t))
    )


def file_lines(path: str) -> int:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f if _.strip())
    except FileNotFoundError:
        return 0


def gen_fill(lengths: List[int], q: queue.Queue, n_workers: int, reset=False):
    if reset:
        clear_progress()
    last  = load_progress()
    skip  = last is not None
    count = 0
    for combo in gen_tiered(lengths):
        if skip:
            if combo == last:
                skip = False
            else:
                continue
        q.put(combo)
        count += 1
    log.info(f"gen fill done — {count} combos")
    for _ in range(n_workers):
        q.put(None)


def precision_fill(lengths: List[int], q: queue.Queue, n_workers: int):
    count = 0
    for combo in gen_precision(lengths):
        q.put(combo)
        count += 1
    log.info(f"precision fill done — {count} combos")
    for _ in range(n_workers):
        q.put(None)


def file_fill(path: str, q: queue.Queue, n_workers: int):
    count = 0
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                c = line.strip()
                if c:
                    q.put(c)
                    count += 1
    except FileNotFoundError:
        log.error(f"targets not found: {path}")
    log.info(f"file fill done — {count}")
    for _ in range(n_workers):
        q.put(None)


class RollingRPS:
    def __init__(self, window=5.0):
        self._w    = window
        self._t: Deque[float] = deque()
        self._lock = threading.Lock()

    def record(self):
        now = time.monotonic()
        with self._lock:
            self._t.append(now)
            self._prune(now)

    def get(self) -> float:
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            return len(self._t) / self._w

    def _prune(self, now: float):
        c = now - self._w
        while self._t and self._t[0] < c:
            self._t.popleft()


class Bucket:
    def __init__(self, rate: float, burst=3):
        self._rate   = rate
        self._burst  = float(burst)
        self._tokens = float(burst)
        self._last   = time.monotonic()
        self._lock   = threading.Lock()

    def acquire(self):
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(
                    self._burst,
                    self._tokens + (now - self._last) * self._rate,
                )
                self._last = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait = (1.0 - self._tokens) / self._rate
            time.sleep(wait)


class Saver:
    def __init__(self, interval: int, flock: threading.Lock):
        self._n    = interval
        self._fl   = flock
        self._lock = threading.Lock()
        self._i    = 0
        self._last = ""

    def update(self, combo: str):
        with self._lock:
            self._last = combo
            self._i   += 1
            should = self._i >= self._n
            if should:
                self._i = 0
                v = self._last
        if should:
            self._write(v)

    def flush(self):
        with self._lock:
            v = self._last
        if v:
            self._write(v)

    def _write(self, v: str):
        with self._fl:
            try:
                tmp = PROG_FILE + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(v)
                os.replace(tmp, PROG_FILE)
            except OSError as e:
                log.warning(f"progress write: {e}")


def load_progress() -> Optional[str]:
    try:
        with open(PROG_FILE, "r", encoding="utf-8") as f:
            return f.read().strip() or None
    except FileNotFoundError:
        return None


def clear_progress():
    try:
        os.remove(PROG_FILE)
    except (FileNotFoundError, OSError):
        pass


# ── display ───────────────────────────────────────────────────────────────────
#
# fixed-height in-place terminal panel — always exactly PANEL_H lines tall.
# redrawn in place every frame using ANSI cursor-up (\033[NA) + erase-line
# (\r\033[2K) sequences. the height never changes so there is no wrapping
# or drift — that was the root cause of the "stretching" bug in v2.5.x.
#
# layout  (PANEL_H = MAX_HITS + 4 = 9 lines):
#   line 0      message (rate-limit / error notice, 5s ttl)
#   line 1      ─── separator ──────────────────────────────
#   lines 2-6   hit slots (newest first, 10s ttl each)
#   line 7      ─── separator ──────────────────────────────
#   line 8      stats (checked / hits / taken / rps / eta)
#
# bugs fixed vs v2.5.2:
#   1. ANSI padding: format width spec (:<N) counts invisible escape codes,
#      producing wrong alignment. fixed by padding the raw string first,
#      then wrapping in color codes.
#   2. stop() cursor math: the old stop() moved up, wrote blank lines
#      (which moved the cursor DOWN past the panel), then tried to move up
#      again — leaving the cursor in the wrong place and orphaning content.
#      fixed: just erase each line in place, no extra moves.
#   3. errors counter: show_bar now passes errors to Display.update()
#      so errors appear in the stats line.

class Display:
    MAX_HITS = 5
    HIT_TTL  = 10.0
    MSG_TTL  = 5.0

    def __init__(self, lock: threading.Lock, total: int, mode_label: str):
        self._lock   = lock
        self._total  = total
        self._label  = mode_label
        self._hits: List[tuple] = []   # (combo, hit_n, rps, ts)
        self._msg    = ""
        self._msg_ts = 0.0
        self._drawn  = False
        self._h      = self.MAX_HITS + 4   # total panel height in lines

    @staticmethod
    def _abbrev(n: int) -> str:
        if n >= 1_000_000: return f"{n / 1_000_000:.1f}M"
        if n >= 10_000:    return f"{n // 1_000}K"
        if n >= 1_000:     return f"{n / 1_000:.1f}K"
        return str(n)

    @staticmethod
    def _pad(s: str, width: int) -> str:
        # pad the raw string to `width` chars, then it's safe to wrap in styles
        return s + " " * max(0, width - len(s))

    def start(self):
        with self._lock:
            sys.stdout.write(f"\n  {green('+')} starting {self._label} ...\n\n")
            sys.stdout.flush()
            self._paint(0, 0, 0, 0, 0.0, "--")

    def stop(self):
        # erase the panel in place: move up to top of panel, clear each line
        # (no second cursor-up — that was the v2.5.2 stop() bug)
        with self._lock:
            if self._drawn:
                sys.stdout.write(f"\033[{self._h}A")
                for _ in range(self._h):
                    sys.stdout.write("\r\033[2K\n")
                sys.stdout.write(f"\033[{self._h}A")
                sys.stdout.flush()
            self._drawn = False

    def add_hit(self, combo: str, hit_n: int, rps: float):
        with self._lock:
            self._hits.append((combo, hit_n, rps, time.monotonic()))

    def set_msg(self, text: str):
        with self._lock:
            self._msg    = text
            self._msg_ts = time.monotonic()

    def update(self, checked: int, hits: int, taken: int, errors: int, rps: float, eta: str):
        with self._lock:
            self._paint(checked, hits, taken, errors, rps, eta)

    def _paint(self, checked: int, hits: int, taken: int, errors: int, rps: float, eta: str):
        now = time.monotonic()

        # expire hits older than HIT_TTL
        self._hits = [(c, n, r, t) for c, n, r, t in self._hits if now - t < self.HIT_TTL]

        # move cursor to top of panel on subsequent frames
        if self._drawn:
            sys.stdout.write(f"\033[{self._h}A")

        def _ln(content: str = ""):
            sys.stdout.write(f"\r\033[2K{content}\n")

        # line 0: message with ttl
        if self._msg and (now - self._msg_ts) < self.MSG_TTL:
            _ln(f"  {yellow(self._msg)}")
        else:
            self._msg = ""
            _ln()

        # line 1: top separator
        _ln(f"  {gray(H * W)}")

        # lines 2..2+MAX_HITS-1: hit slots, newest first
        visible = list(reversed(self._hits))[:self.MAX_HITS]
        for i in range(self.MAX_HITS):
            if i < len(visible):
                c, n, r, t = visible[i]
                age   = int(now - t)
                age_s = "just now" if age == 0 else f"{age}s ago"
                # pad raw combo string FIRST, then apply styles — fixes ANSI width bug
                padded = self._pad(c, 6)
                _ln(f"  {green('+')}"
                    f"  {bold(green(padded))}"
                    f"  {gray(f'hit #{n}  ·  {r:.0f} r/s  ·  {age_s}')}")
            else:
                _ln()

        # line MAX_HITS+2: bottom separator
        _ln(f"  {gray(H * W)}")

        # line MAX_HITS+3: stats — abbreviated numbers keep line short
        total = self._total
        pct   = f" ({checked / total * 100:.1f}%)" if total > 0 else ""
        err_s = f"  {gray('errors:')} {self._abbrev(errors)}" if errors > 0 else ""
        _ln(
            f"  {gray('checked:')} {self._abbrev(checked)}/{self._abbrev(total)}{pct}"
            f"  {gray('hits:')} {green(str(hits))}"
            f"  {gray('taken:')} {self._abbrev(taken)}"
            f"{err_s}"
            f"  {gray('rps:')} {rps:.0f}"
            f"  {gray('eta:')} {eta}"
        )

        sys.stdout.flush()
        self._drawn = True


# ── webhook ───────────────────────────────────────────────────────────────────
#
# sends a minimal discord embed on free hit.
# white left stripe (color 0xffffff) — clean and neutral.
# daemon thread — workers never block waiting for delivery.

class Webhook:
    def __init__(self, urls: List[str]):
        _need_requests()
        self._urls = urls
        self._q: queue.Queue = queue.Queue()
        self._s = requests.Session()
        self._s.headers["content-type"] = "application/json"
        if urls:
            threading.Thread(target=self._loop, daemon=True, name="hook").start()

    def fire(self, combo: str, rps: float, hits: int):
        if self._urls:
            self._q.put((combo, rps, hits))

    def test(self, url: str) -> bool:
        try:
            r = self._s.post(url, json=self._test_body(), timeout=8)
            return r.status_code in (200, 204)
        except Exception:
            return False

    def _loop(self):
        while True:
            combo, rps, hits = self._q.get()
            for url in self._urls:
                try:
                    r = self._s.post(url, json=self._hit_body(combo, rps, hits), timeout=8)
                    if r.status_code not in (200, 204):
                        log.warning(f"webhook {url[:40]} {ARROW} {r.status_code}")
                except Exception as e:
                    log.warning(f"webhook failed: {e}")

    @staticmethod
    def _hit_body(combo: str, rps: float, hits: int) -> dict:
        return {
            "embeds": [{
                "description": f"`{combo}`",
                "color":       0xffffff,
                "fields": [
                    {"name": "hit",  "value": f"#{hits}",       "inline": True},
                    {"name": "rps",  "value": f"{rps:.0f}",     "inline": True},
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer":    {"text": f"bulwark v{VERSION}"},
            }]
        }

    @staticmethod
    def _test_body() -> dict:
        return {
            "embeds": [{
                "description": "webhook connected.",
                "color":       0xffffff,
                "footer":      {"text": f"bulwark v{VERSION}"},
            }]
        }


_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]
_ACCEPTS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "application/json, text/plain, */*",
]


def mk_sess(token: str, proxy: Optional[str] = None):
    _need_requests()
    sess = requests.Session()
    try:
        retry = _Retry(total=3, backoff_factor=0.5, status_forcelist=[500,502,503,504], allowed_methods=["POST"])
    except TypeError:
        retry = _Retry(total=3, backoff_factor=0.5, status_forcelist=[500,502,503,504], method_whitelist=["POST"])
    sess.mount("https://", HTTPAdapter(max_retries=retry))
    sess.headers.update({
        "authorization":      token,
        "content-type":       "application/json",
        "user-agent":         random.choice(_UAS),
        "accept":             random.choice(_ACCEPTS),
        "accept-language":    "en-US,en;q=0.9",
        "sec-ch-ua":          '"Chromium";v="125", "Not.A/Brand";v="24"',
        "sec-ch-ua-mobile":   "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest":     "empty",
        "sec-fetch-mode":     "cors",
        "sec-fetch-site":     "same-origin",
    })
    if proxy:
        sess.proxies = {"https": proxy, "http": proxy}
    return sess


def worker(q, token, wid, bucket, flock, stop, stats, slock, proxy, outfile, saver, rps, hook, disp):
    sess = mk_sess(token, proxy)
    while not stop.is_set():
        try:
            combo = q.get(timeout=3)
        except queue.Empty:
            continue
        if combo is None:
            q.task_done()
            break
        saver.update(combo)
        do_check(sess, combo, wid, q, flock, stop, stats, slock, bucket, outfile, rps, hook, disp)
        q.task_done()
    sess.close()


def do_check(sess, combo, wid, q, flock, stop, stats, slock, bucket, outfile, rps, hook, disp):
    for attempt in range(5):
        if stop.is_set():
            return

        bucket.acquire()
        time.sleep(random.uniform(*JITTER))

        try:
            r = sess.post(API_URL, data=json.dumps({"username": combo}), timeout=12)
        except requests.ConnectionError:
            wait = min(2 ** attempt, 30)
            log.warning(f"connection error {combo} (attempt {attempt+1}) — wait {wait}s")
            time.sleep(wait)
            continue
        except requests.Timeout:
            log.warning(f"timeout {combo} (attempt {attempt+1})")
            time.sleep(1)
            continue
        except requests.RequestException as e:
            log.error(f"req error {combo}: {e}")
            with slock:
                stats["errors"] += 1
                stats["total"]  += 1
            return

        rps.record()

        if r.status_code == 200:
            body     = _jparse(r)
            is_taken = body.get("taken", False)
            if is_taken:
                with slock:
                    stats["taken"] += 1
                    stats["total"] += 1
                log.debug(f"taken (200): {combo}")
            else:
                cur_rps = rps.get()
                with slock:
                    stats["hits"]  += 1
                    stats["total"] += 1
                    hits = stats["hits"]
                _save_free(combo, flock, outfile)
                hook.fire(combo, cur_rps, hits)
                log.info(f"free: {combo}")
                disp.add_hit(combo, hits, cur_rps)
            return

        if r.status_code == 400:
            body = _jparse(r)
            if body.get("code") == 50035 or "USERNAME_ALREADY_TAKEN" in r.text:
                with slock:
                    stats["taken"] += 1
                    stats["total"] += 1
                log.debug(f"taken (400): {combo}")
            else:
                msg = body.get("message", r.text[:80])
                log.warning(f"400 {combo}: {msg}")
                with slock:
                    stats["errors"] += 1
                    stats["total"]  += 1
                disp.set_msg(f"400 ({combo}): {msg}")
            return

        if r.status_code == 429:
            body = _jparse(r)
            wait = float(body.get("retry_after", 3.0))
            if wait > 300:
                wait /= 1000.0
            log.warning(f"429 {combo} — {wait:.1f}s (attempt {attempt+1})")
            disp.set_msg(f"rate limited — sleeping {wait:.1f}s")
            time.sleep(wait)
            continue

        if r.status_code == 401:
            disp.set_msg("invalid token — update in settings")
            log.error("401 — stopping")
            stop.set()
            return

        if r.status_code == 403:
            disp.set_msg("forbidden (403) — try a proxy")
            log.error(f"403 — stopping ({r.text[:80]})")
            stop.set()
            return

        log.warning(f"unexpected {r.status_code} on {combo}")
        with slock:
            stats["errors"] += 1
            stats["total"]  += 1
        return

    try:
        q.put(combo, timeout=10)
    except queue.Full:
        log.error(f"queue full, dropping {combo}")


def _save_free(combo: str, lock: threading.Lock, outfile: str):
    with lock:
        Path(outfile).parent.mkdir(parents=True, exist_ok=True)
        with open(outfile, "a", encoding="utf-8") as f:
            f.write(combo + "\n")


def _jparse(r) -> dict:
    try:
        return r.json()
    except Exception:
        return {}


def show_bar(stats, slock, rps_obj, start, stop, disp):
    while not stop.is_set():
        with slock:
            s = dict(stats)
        r       = rps_obj.get()
        elapsed = time.time() - start
        eta     = "--"
        total   = disp._total
        if total > 0 and r > 0:
            rem = max(0.0, (total - s["total"]) / r)
            eta = _fmtt(rem) if rem > 0 else "done"
        disp.update(s["total"], s["hits"], s["taken"], s["errors"], r, eta)
        time.sleep(0.25)


def log_stats(stats, slock, start, stop):
    while not stop.is_set():
        time.sleep(60)
        with slock:
            s = dict(stats)
        e    = time.time() - start
        rate = s["total"] / e if e else 0
        log.info(
            f"checked={s['total']} hits={s['hits']} "
            f"taken={s['taken']} errors={s['errors']} rate={rate:.1f}/s"
        )


def _fmtt(secs: float) -> str:
    if secs < 60:   return f"{secs:.0f}s"
    if secs < 3600: return f"{secs/60:.0f}m"
    return f"{int(secs//3600)}h {int((secs%3600)//60)}m"


def run(cfg: Dict, total: int, filler: Callable, mode_label: str = "checker") -> Dict:
    _need_requests()
    wq     = queue.Queue(maxsize=2000)
    bucket = Bucket(rate=cfg["rate"], burst=3)
    flock  = threading.Lock()
    plock  = threading.Lock()
    stop   = threading.Event()
    slock  = threading.Lock()
    stats  = {"hits": 0, "taken": 0, "errors": 0, "total": 0}
    saver  = Saver(FLUSH_EVERY, flock)
    rps    = RollingRPS()
    hook   = Webhook(cfg["webhooks"])
    disp   = Display(plock, total, mode_label)
    start  = time.time()
    out    = rp(cfg["output"])

    disp.start()

    threading.Thread(target=filler, args=(wq, cfg["threads"]), daemon=True, name="gen").start()

    workers = []
    for i in range(cfg["threads"]):
        t = threading.Thread(
            target=worker,
            args=(wq, cfg["token"], i+1, bucket, flock, stop, stats, slock,
                  cfg["proxy"], out, saver, rps, hook, disp),
            daemon=True, name=f"w{i+1}",
        )
        t.start()
        workers.append(t)

    threading.Thread(target=show_bar,  args=(stats, slock, rps, start, stop, disp), daemon=True, name="bar").start()
    threading.Thread(target=log_stats, args=(stats, slock, start, stop),             daemon=True, name="log").start()

    try:
        for t in workers:
            t.join()
    except KeyboardInterrupt:
        stop.set()
        for t in workers:
            t.join(timeout=3)

    stop.set()
    disp.stop()
    saver.flush()

    elapsed = time.time() - start
    with slock:
        final = dict(stats)
    final["elapsed"] = elapsed
    return final


def mode_gen(cfg: Dict):
    lengths = cfg["lengths"]
    out     = rp(cfg["targets_file"])
    try:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"\n  error: {e}\n"); return

    print()
    print(f"  {bold('generator')}")
    print(SEP)
    print(f"  lengths    {', '.join(str(n) for n in lengths)} chars")
    print(f"  output     {out}")
    print(f"  data       {BASE}")
    print()
    print(f"  {gray('counting ...')}", end="", flush=True)
    total = combo_count_cached(cfg, lengths)
    print(f"\r  total      {bold(f'{total:,}')} combos")
    print()

    if not _confirm("  write targets file? [y/n]  › "):
        print(gray("\n  cancelled.\n")); return

    print()
    written = 0
    try:
        with open(out, "w", encoding="utf-8") as f:
            for combo in gen_tiered(lengths):
                f.write(combo + "\n")
                written += 1
                if written % 5000 == 0:
                    pct = written / total * 100 if total else 0
                    sys.stdout.write(f"\r  {gray(f'writing {written:,} / {total:,} ({pct:.0f}%)')}")
                    sys.stdout.flush()
    except OSError as e:
        print(f"\n  error: {e}\n"); return

    print(f"\r  done  {bold(f'{written:,}')} combos {ARROW} {bold(out)}  ")
    print()
    if not NON_INTERACTIVE:
        input(gray("  enter to continue  › "))


def mode_check(cfg: Dict):
    if not cfg["token"]:
        _no_token(); return

    tgt   = rp(cfg["targets_file"])
    total = file_lines(tgt)

    print()
    print(f"  {bold('checker')}")
    print(SEP)
    print(f"  targets    {tgt}")
    print(f"  entries    {f'{total:,}' if total else gray('not found')}")
    print(f"  threads    {cfg['threads']}")
    print(f"  rate       {cfg['rate']} req/s")
    print(f"  proxy      {cfg['proxy'] or 'none'}")
    print(f"  output     {rp(cfg['output'])}")
    print(f"  webhooks   {len(cfg['webhooks'])}")
    print()

    if total == 0:
        print(f"  run {bold('generator')} first.\n")
        if not NON_INTERACTIVE:
            input(gray("  enter  › "))
        return

    if not _confirm("  start? [y/n]  › "):
        print(gray("\n  cancelled.\n")); return

    print()
    log.info(f"checker — {tgt} {total} entries")
    final = run(cfg, total, lambda q, n: file_fill(tgt, q, n), "checker")
    _summary(final, rp(cfg["output"]))
    if not NON_INTERACTIVE:
        input(gray("\n  enter to return  › "))


def mode_marksman(cfg: Dict):
    if not cfg["token"]:
        _no_token(); return

    lengths = cfg["lengths"]
    print()
    print(f"  {bold('marksman')}")
    print(SEP)
    print(f"  lengths    {', '.join(str(n) for n in lengths)} chars")
    print(f"  threads    {cfg['threads']}")
    print(f"  rate       {cfg['rate']} req/s")
    print(f"  proxy      {cfg['proxy'] or 'none'}")
    print(f"  output     {rp(cfg['output'])}")
    print(f"  webhooks   {len(cfg['webhooks'])}")
    print(f"  order      exhaustive — tiered + rarity")

    last = load_progress()
    if last:
        print(f"  checkpoint {bold(last)}")

    print()
    print(f"  {gray('counting ...')}", end="", flush=True)
    total = combo_count_cached(cfg, lengths)
    print(f"\r  total      {bold(f'{total:,}')} combos           ")
    print()

    reset = False
    if last:
        if NON_INTERACTIVE:
            reset = RESUME_POLICY == "reset"
        else:
            reset = input(gray("  resume from checkpoint? [y/n]  › ")).strip().lower() == "n"
            print()

    if not _confirm("  start? [y/n]  › "):
        print(gray("\n  cancelled.\n")); return

    print()
    log.info(f"marksman — lengths={lengths} threads={cfg['threads']} rate={cfg['rate']} total={total}")
    final = run(cfg, total, lambda q, n: gen_fill(lengths, q, n, reset=reset), "marksman")
    _summary(final, rp(cfg["output"]))
    if not NON_INTERACTIVE:
        input(gray("\n  enter to return  › "))


def mode_precision(cfg: Dict):
    if not cfg["token"]:
        _no_token(); return

    lengths = cfg["lengths"]
    print()
    print(f"  {bold('precision')}")
    print(SEP)
    print(f"  lengths    {', '.join(str(n) for n in lengths)} chars")
    print(f"  threads    {cfg['threads']}")
    print(f"  rate       {cfg['rate']} req/s")
    print(f"  proxy      {cfg['proxy'] or 'none'}")
    print(f"  output     {rp(cfg['output'])}")
    print(f"  webhooks   {len(cfg['webhooks'])}")
    print(f"  order      6-wave rarity priority")
    print()
    print(f"  {gray('wave 1')}  3-char · rare letters first")
    print(f"  {gray('wave 2')}  4-char letters+digits (1-2 digits) · rare first")
    print(f"  {gray('wave 3')}  3-char · no rare letter")
    print(f"  {gray('wave 4')}  4-char letters+digits · no rare")
    print(f"  {gray('wave 5')}  4-char pure letters · rare first")
    print(f"  {gray('wave 6')}  4-char pure letters · no rare")
    print()
    print(f"  {gray('estimating ...')}", end="", flush=True)
    total = combo_count_cached(cfg, lengths, "|precision")
    print(f"\r  total      {bold(f'{total:,}')} combos                    ")
    print()

    if not _confirm("  start? [y/n]  › "):
        print(gray("\n  cancelled.\n")); return

    print()
    log.info(f"precision — lengths={lengths} threads={cfg['threads']} rate={cfg['rate']} total={total}")
    final = run(cfg, total, lambda q, n: precision_fill(lengths, q, n), "precision")
    _summary(final, rp(cfg["output"]))
    if not NON_INTERACTIVE:
        input(gray("\n  enter to return  › "))


def mode_settings(cfg: Dict):
    while True:
        _cls()
        print()
        print(f"  {bold('settings')}")
        print(SEP)
        print(f"  {gray('data')}  {BASE}")
        print()

        tok  = _mask(cfg["token"]) if cfg["token"] else gray("not set")
        rows = [
            ("1", "token",        tok),
            ("2", "threads",      str(cfg["threads"])),
            ("3", "rate",         f"{cfg['rate']} req/s"),
            ("4", "lengths",      ", ".join(str(n) for n in cfg["lengths"]) + " chars"),
            ("5", "proxy",        cfg["proxy"] or gray("none")),
            ("6", "output file",  cfg["output"]),
            ("7", "targets file", cfg["targets_file"]),
            ("8", "webhooks",     f"{len(cfg['webhooks'])} configured  {ARROW}"),
            ("9", "back",         ""),
        ]
        for k, label, val in rows:
            tail = f"  {gray(val)}" if val else ""
            print(f"  {gray(k)}  {label:<16}{tail}")

        print()
        ch = input(gray("  select  › ")).strip()

        if   ch == "1": _set_token(cfg)
        elif ch == "2": _set_int(cfg,   "threads",      "threads",      1,   100)
        elif ch == "3": _set_float(cfg, "rate",         "rate (req/s)", 0.1, 50.0)
        elif ch == "4": _set_lengths(cfg)
        elif ch == "5": _set_proxy(cfg)
        elif ch == "6": _set_str(cfg,   "output",       "output file",  FREE_DEF)
        elif ch == "7": _set_str(cfg,   "targets_file", "targets file", TGTS_DEF)
        elif ch == "8": _webhooks(cfg)
        elif ch == "9": break


def _set_token(cfg):
    print()
    print(gray("  paste your token and press enter."))
    print()
    v = getpass("  token  › ").strip()
    if v:
        cfg["token"] = v; save_cfg(cfg)
        print(gray("\n  saved.\n"))
    else:
        print(gray("\n  no change.\n"))
    time.sleep(0.4)

def _set_int(cfg, key, label, lo, hi):
    print()
    v = input(f"  {label} [{lo}-{hi}] (now: {cfg[key]})  › ").strip()
    try:
        n = int(v); assert lo <= n <= hi
        cfg[key] = n; save_cfg(cfg)
        print(gray(f"\n  {label} {ARROW} {n}\n"))
    except (ValueError, AssertionError):
        print(gray("\n  invalid.\n"))
    time.sleep(0.4)

def _set_float(cfg, key, label, lo, hi):
    print()
    v = input(f"  {label} [{lo}-{hi}] (now: {cfg[key]})  › ").strip()
    try:
        n = float(v); assert lo <= n <= hi
        cfg[key] = n; save_cfg(cfg)
        print(gray(f"\n  {label} {ARROW} {n}\n"))
    except (ValueError, AssertionError):
        print(gray("\n  invalid.\n"))
    time.sleep(0.4)

def _set_lengths(cfg):
    print()
    v = input("  lengths (3 / 4 / 3,4)  › ").strip()
    try:
        lengths = sorted({int(x.strip()) for x in v.split(",")})
        assert lengths and all(n in (3, 4) for n in lengths)
        cfg["lengths"] = lengths; save_cfg(cfg)
        print(gray(f"\n  lengths {ARROW} {', '.join(str(n) for n in lengths)}\n"))
    except (ValueError, AssertionError):
        print(gray("\n  invalid.\n"))
    time.sleep(0.4)

def _set_proxy(cfg):
    print()
    print(gray("  http://user:pass@host:port  (blank to clear)"))
    v = input("  proxy  › ").strip()
    cfg["proxy"] = v or None; save_cfg(cfg)
    print(gray(f"\n  {'proxy ' + ARROW + ' ' + v if v else 'cleared'}\n"))
    time.sleep(0.4)

def _set_str(cfg, key, label, default):
    print()
    v = input(f"  {label} (now: {cfg[key]})  › ").strip()
    cfg[key] = rp(v) if v else default; save_cfg(cfg)
    print(gray(f"\n  {label} {ARROW} {cfg[key]}\n"))
    time.sleep(0.4)

def _webhooks(cfg):
    while True:
        _cls()
        print()
        print(f"  {bold('webhooks')}")
        print(SEP)
        print(gray("  sends a minimal embed when a free username is found."))
        print()
        if cfg["webhooks"]:
            for i, url in enumerate(cfg["webhooks"], 1):
                print(f"  {gray(str(i))}  {_trim(url)}")
        else:
            print(gray("  none configured."))
        print()
        print(f"  {gray('a')}  add")
        if cfg["webhooks"]:
            print(f"  {gray('r')}  remove")
            print(f"  {gray('t')}  test all")
        print(f"  {gray('b')}  back")
        print()

        ch = input(gray("  select  › ")).strip().lower()

        if ch == "a":
            print()
            print(gray("  https://discord.com/api/webhooks/ID/TOKEN"))
            url = input("  url  › ").strip()
            if url.startswith("https://discord.com/api/webhooks/"):
                cfg["webhooks"].append(url); save_cfg(cfg)
                print(gray("\n  added.\n"))
            else:
                print(gray("\n  invalid url.\n"))
            time.sleep(0.5)

        elif ch == "r" and cfg["webhooks"]:
            print()
            idx = input(f"  remove # [1-{len(cfg['webhooks'])}]  › ").strip()
            try:
                i = int(idx) - 1
                assert 0 <= i < len(cfg["webhooks"])
                removed = cfg["webhooks"].pop(i); save_cfg(cfg)
                print(gray(f"\n  removed: {_trim(removed)}\n"))
            except (ValueError, AssertionError):
                print(gray("\n  invalid.\n"))
            time.sleep(0.5)

        elif ch == "t" and cfg["webhooks"]:
            wh = Webhook([])
            print()
            for url in cfg["webhooks"]:
                ok = wh.test(url)
                print(f"  {_trim(url)}  {gray(ARROW)}  {gray('ok') if ok else red('failed')}")
            print()
            if not NON_INTERACTIVE:
                input(gray("  enter  › "))

        elif ch == "b":
            break


def menu():
    cfg = load_cfg()
    while True:
        _cls()
        print()
        print(LOGO)
        print()
        print(f"  {gray(QUOTE)}")
        print()
        print(f"  {bold('bulwark')}  {gray('·  ' + DISCORD_LINK)}")
        print(SEP)
        print()
        print(f"  {gray('1')}  generator      {gray('generate a target list')}")
        print(f"  {gray('2')}  checker        {gray('check from a target file')}")
        print(f"  {gray('3')}  marksman       {gray('exhaustive — all combos, tiered + rarity')}")
        print(f"  {gray('4')}  precision      {gray('focused — 6-wave inline, letter+digit mix')}")
        print(f"  {gray('5')}  settings       {gray('token, threads, rate, webhooks')}")
        print(f"  {gray('q')}  quit")
        print()

        if not cfg["token"]:
            print(gray("  token not set — go to settings."))
            print()

        ch = input(gray("  select  › ")).strip().lower()

        if   ch == "1": mode_gen(cfg)
        elif ch == "2": mode_check(cfg)
        elif ch == "3": mode_marksman(cfg)
        elif ch == "4": mode_precision(cfg)
        elif ch == "5":
            mode_settings(cfg)
            cfg = load_cfg()
        elif ch in ("q", "quit", "exit"):
            print(); break


def _cls():  os.system("cls" if os.name == "nt" else "clear")

def _confirm(p):
    if NON_INTERACTIVE: return True
    return input(p).strip().lower() == "y"

def _no_token():
    print(f"\n  {bold('no token')} — set it in settings first.\n")
    if not NON_INTERACTIVE:
        input(gray("  enter  › "))

def _mask(t):
    if len(t) <= 8: return "xxxxxxxx"
    return t[:4] + "xxxx" + t[-4:]

def _trim(url, n=62):
    return url if len(url) <= n else url[:n] + "..."

def _summary(s: Dict, outfile: str):
    elapsed = s.get("elapsed", 0.0)
    rate    = s["total"] / elapsed if elapsed else 0
    total   = s["total"]
    print()
    print(f"\n  {gray(H * W)}")
    print(f"  {bold('summary')}")
    print(f"  checked   {bold(f'{total:,}')}")
    print(f"  hits      {bold(green(str(s['hits'])))}")
    print(f"  taken     {s['taken']:,}")
    print(f"  errors    {s['errors']}")
    print(f"  rate avg  {rate:.1f} req/s")
    print(f"  elapsed   {_fmtt(elapsed)}")
    if s["hits"]:
        print(f"\n  saved to  {bold(outfile)}")


def _plengths(s):
    lengths = sorted({int(x.strip()) for x in s.split(",") if x.strip()})
    if not lengths or any(n not in (3, 4) for n in lengths):
        raise ValueError
    return lengths


def cli(argv):
    p = argparse.ArgumentParser(prog="bulwark")
    p.add_argument("--version", "-v",   action="store_true")
    p.add_argument("--where",           action="store_true")
    p.add_argument("--reset-progress",  action="store_true")
    p.add_argument("--mode", choices=["menu","generator","checker","marksman","precision"], default="menu")
    p.add_argument("--yes",             action="store_true")
    p.add_argument("--resume", choices=["resume","reset"], default="resume")
    p.add_argument("--token")
    p.add_argument("--threads", type=int)
    p.add_argument("--rate",    type=float)
    p.add_argument("--lengths")
    p.add_argument("--proxy")
    p.add_argument("--output")
    p.add_argument("--targets-file", dest="targets_file")
    p.add_argument("--webhook", action="append")
    args = p.parse_args(argv)

    if args.version:
        print(VERSION); return 0

    cfg = load_cfg()

    if args.where:
        print(f"data:     {BASE}\nconfig:   {CFG_FILE}\nlog:      {LOG_FILE}\nprogress: {PROG_FILE}")
        print(f"targets:  {rp(cfg['targets_file'])}\noutput:   {rp(cfg['output'])}")
        return 0

    if args.reset_progress:
        clear_progress(); print("progress cleared."); return 0

    if args.token is None and not cfg.get("token"):
        env = os.getenv("BULWARK_TOKEN", "").strip()
        if env:
            cfg["token"] = env

    dirty = False
    if args.token        is not None: cfg["token"]        = args.token.strip();                     dirty = True
    if args.threads      is not None: cfg["threads"]      = max(1, min(100, args.threads));         dirty = True
    if args.rate         is not None: cfg["rate"]         = max(0.1, min(50.0, args.rate));         dirty = True
    if args.lengths      is not None: cfg["lengths"]      = _plengths(args.lengths);                dirty = True
    if args.proxy        is not None: cfg["proxy"]        = args.proxy.strip() or None;             dirty = True
    if args.output       is not None: cfg["output"]       = args.output.strip() or FREE_DEF;        dirty = True
    if args.targets_file is not None: cfg["targets_file"] = args.targets_file.strip() or TGTS_DEF;  dirty = True
    if args.webhook:
        cfg.setdefault("webhooks", [])
        cfg["webhooks"] += [u.strip() for u in args.webhook if (u or "").strip()]
        dirty = True
    if dirty:
        save_cfg(cfg)

    if args.mode == "menu":
        menu(); return 0

    global NON_INTERACTIVE, RESUME_POLICY
    NON_INTERACTIVE = True
    RESUME_POLICY   = args.resume

    if not args.yes and args.mode in ("generator","checker","marksman","precision"):
        print(f"pass --yes for non-interactive {args.mode}."); return 2

    if args.mode in ("checker","marksman","precision") and not cfg.get("token"):
        print("no token — pass --token or set in settings."); return 2

    if   args.mode == "generator": mode_gen(cfg)
    elif args.mode == "checker":   mode_check(cfg)
    elif args.mode == "marksman":  mode_marksman(cfg)
    elif args.mode == "precision": mode_precision(cfg)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(cli(sys.argv[1:]))
    except KeyboardInterrupt:
        print("\n")
        sys.exit(0)