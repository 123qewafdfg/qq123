#!/usr/bin/env python3
"""本地预览服务器 —— 目的是尽量贴近线上环境，而不是 file:// 离线打开。

它比 `python -m http.server` 多做三件事：
  1. 给 CSS / JS / HTML 明确返回 charset=utf-8（python 自带的只有裸 MIME，
     中文在按 GBK 猜编码的浏览器上会乱码）
  2. 读取并应用项目里的 `_headers` 文件（Cloudflare Workers 静态资源的行为），
     这样本地就能验证 CSP 会不会把 WASM 拦掉
  3. 关闭缓存，避免刷新后看到旧文件

用法： python serve.py [port]
"""
import sys
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))

# 显式 charset，避免浏览器对 text/css、text/javascript 按本地编码猜测
CHARSET_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".jsonc": "application/json; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".wasm": "application/wasm",
    ".ico": "image/x-icon",
}
# 这些明确不要 charset（二进制 / 已自带编码）
NO_CHARSET = {".wasm", ".ico", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}


def load_headers_file(path):
    """解析 Cloudflare `_headers` 格式，返回 [(pattern, {header: value}), ...]"""
    rules = []
    if not os.path.exists(path):
        return rules
    with open(path, "r", encoding="utf-8") as fh:
        current = None
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if not line[0].isspace():
                current = (line.strip(), {})
                rules.append(current)
            elif current is not None:
                if ":" in line:
                    key, _, value = line.strip().partition(":")
                    current[1][key.strip()] = value.strip()
    return rules


def match_headers(rules, url_path):
    """返回匹配该路径的头部。越具体的规则放后面覆盖前面的（与 Cloudflare 行为一致）。"""
    result = {}
    for pattern, headers in rules:
        if pattern == "/*":
            result.update(headers)
        elif pattern.endswith("*"):
            prefix = pattern[:-1]
            if url_path.startswith(prefix):
                result.update(headers)
        elif pattern == url_path:
            result.update(headers)
    return result


HEADER_RULES = load_headers_file(os.path.join(ROOT, "_headers"))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in CHARSET_TYPES:
            return CHARSET_TYPES[ext]
        return super().guess_type(path)

    def end_headers(self):
        url_path = self.path.split("?")[0]
        for key, value in match_headers(HEADER_RULES, url_path).items():
            self.send_header(key, value)
        # 本地预览不需要缓存，否则改了文件刷新看不到
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8123
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"serving {ROOT}")
    print(f"http://127.0.0.1:{port}/")
    print(f"_headers rules loaded: {len(HEADER_RULES)}")
    global_rules = match_headers(HEADER_RULES, "/index.html")
    csp = global_rules.get("Content-Security-Policy")
    print("CSP active: %s" % ("yes" if csp else "no"))
    if csp:
        print("  " + csp)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
