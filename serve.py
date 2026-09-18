#!/usr/bin/env python3
"""本地预览服务器 —— 目的是尽量贴近线上环境，而不是 file:// 离线打开。

它比 `python -m http.server` 多做四件事：
  1. 给 CSS / JS / HTML 明确返回 charset=utf-8（python 自带的只有裸 MIME，
     中文在按 GBK 猜编码的浏览器上会乱码）
  2. 读取并应用项目里的 `_headers` 文件（Cloudflare Workers 静态资源的行为），
     这样本地就能验证 CSP 会不会把 WASM 拦掉
  3. 读取并应用 `.assetsignore`，被排除的文件返回 404 —— 与线上一致，
     可以本地确认文档、许可证、wrangler 配置不会泄漏到公网
  4. 关闭缓存，避免刷新后看到旧文件

用法： python serve.py [port]
"""
import sys
import os
import fnmatch
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


def load_assetsignore(path):
    """读取 `.assetsignore`，返回要排除的文件名/路径模式列表。"""
    patterns = []
    if not os.path.exists(path):
        return patterns
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


ASSETS_IGNORE = load_assetsignore(os.path.join(ROOT, ".assetsignore"))


def is_ignored(url_path):
    """判断某路径是否被 .assetsignore 排除（模拟 Cloudflare 的上传排除行为）。"""
    rel = url_path.lstrip("/")
    if not rel:
        return False
    base = os.path.basename(rel)
    for pat in ASSETS_IGNORE:
        p = pat.lstrip("/")
        if fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(base, p) or rel == p or base == p:
            return True
        # 目录前缀：例如 ".git"
        if rel == p or rel.startswith(p + "/"):
            return True
    return False


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in CHARSET_TYPES:
            return CHARSET_TYPES[ext]
        return super().guess_type(path)

    def do_GET(self):
        url_path = self.path.split("?")[0]
        # 与线上一致：被 .assetsignore 排除的文件不提供
        if is_ignored(url_path):
            body = (
                "<!DOCTYPE html><meta charset=\"utf-8\">"
                "<h1>404 Not Found</h1><p>该文件被 <code>.assetsignore</code> 排除，"
                "线上也不会提供（本地模拟 Cloudflare 的行为）。</p>"
            ).encode("utf-8")
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

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
    # 用法: python serve.py [port] [host]
    #   host 默认 0.0.0.0 —— 绑定所有网卡，手机连同一热点时可直接访问
    #   只在本机看的话可以传 127.0.0.1 更安全
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8123
    host = sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0"
    server = ThreadingHTTPServer((host, port), Handler)

    # 列出可用的局域网地址，方便手机访问
    import socket
    lan_ips = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                lan_ips.append(ip)
    except Exception:
        pass
    # 通过「连一下外网看走哪个网卡」拿到最可能的局域网 IP（不会真的发包）
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.0.2.1", 80))   # TEST-NET-1，仅用于选路
        primary = s.getsockname()[0]
        s.close()
        if primary not in lan_ips:
            lan_ips.insert(0, primary)
        else:
            lan_ips.remove(primary)
            lan_ips.insert(0, primary)
    except Exception:
        pass

    print(f"serving {ROOT}")
    print(f"  local   http://127.0.0.1:{port}/")
    for ip in lan_ips:
        print(f"  LAN     http://{ip}:{port}/")
    if host == "0.0.0.0":
        print("  (已绑定 0.0.0.0 —— 局域网内其它设备可访问；"
              "Windows 首次可能弹出防火墙提示，需允许)")
    print(f"_headers rules loaded: {len(HEADER_RULES)}")
    print(f".assetsignore patterns loaded: {len(ASSETS_IGNORE)}"
          f" -> 这些文件本地与线上都返回 404: {', '.join(ASSETS_IGNORE[:6])}"
          f"{' ...' if len(ASSETS_IGNORE) > 6 else ''}")
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
