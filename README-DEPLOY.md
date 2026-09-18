# 小番茄 · 视频+图片合并版 —— 部署包

这是可直接部署的版本。整个目录就是网站根目录，**428 KB**，无需构建步骤。

```
qq123-deploy/
├── index.html                  # 主页面
├── tb.ico                      # 网站图标
├── _headers                    # Cloudflare 响应头（含 CSP）
├── wrangler.jsonc              # Cloudflare Workers 部署配置
├── .assetsignore               # 指定哪些文件不上传
├── LICENSE                     # 本项目开源协议
├── THIRD-PARTY-NOTICES.md      # 第三方组件版权声明（MIT 合规要求）
├── serve.py                    # 本地预览脚本（已被 .assetsignore 排除，不会上传）
├── css/
│   └── style.css
├── js/
│   ├── app.js                  # 主逻辑（视频解密 + 图片加解密）
│   ├── fastest-obfuscation.js  # 最速混淆算法（请勿修改，需与小程序端兼容）
│   ├── image-wasm-worker.js    # WASM Worker
│   ├── FileSaver.min.js        # 第三方：FileSaver.js 2.0.5
│   └── jszip.min.js            # 第三方：JSZip 3.10.1
└── wasm/
    ├── hilbert_image_cipher_wasm.js
    └── hilbert_image_cipher_wasm_bg.wasm
```

---

## 一、本地预览

**必须通过 HTTP 访问**，不能双击 `index.html`（`file://` 下 WASM 与 Worker 都加载不了，
页面会静默降级成纯 JS 慢速模式）。

```bash
python serve.py 8124
# 然后打开 http://127.0.0.1:8124/
```

不要用 `python -m http.server`——它不返回 `charset=utf-8`，也不读 `_headers`，
在中文 Windows 上会导致 CSS/JS 中文乱码，而且**无法在本地验证 CSP**。

---

## 二、部署到 Cloudflare Workers

`wrangler.jsonc` 已配置好，根目录直接部署：

```bash
npx wrangler deploy
```

Cloudflare 控制台连接的设置：

| 项目 | 值 |
|------|-----|
| Build command | 留空 |
| Deploy command | `npx wrangler deploy` |
| Root directory | `/` |

---

## 三、部署前必须确认的 3 件事

### 1. `Content-Type: application/wasm`

`_headers` 已声明，部署后请实测：

```bash
curl -I https://你的域名/wasm/hilbert_image_cipher_wasm_bg.wasm
# 期望看到: content-type: application/wasm
```

MIME 不对时 wasm-bindgen 会自动回退到较慢的实例化方式，功能仍在但会变慢。

### 2. CSP 是否会拦掉 WASM

`_headers` 里的 CSP 含 `script-src 'self' 'wasm-unsafe-eval'`。
这条指令需要 **Chrome 97+ / Safari 16.4+ / Firefox 102+**。
更老的浏览器会连 WASM 一起拦掉，加解密会静默降级为纯 JS 慢速模式。

> **部署后请用一台真机测一次加密**。如果发现处理异常慢，先把 `_headers` 里
> 那一行 `Content-Security-Policy` 注释掉再试——它不是必需的
> （页面没有 XSS 注入点，CSP 是纵深防御）。

### 3. `.assetsignore` 是否生效

它负责阻止 `LICENSE`、`THIRD-PARTY-NOTICES.md`、`wrangler.jsonc`、`serve.py`
被当成静态资源公开下载。部署后访问一下这些路径，应该返回 404：

```bash
curl -I https://你的域名/wrangler.jsonc   # 期望 404
```

> ⚠️ **这个目录里永远不要放密钥、token 或 `.env` 文件** —— 它们会被一起部署到公网。

---

## 四、已知限制

### 分块打乱的块大小必须整除图片尺寸

分块打乱（Block shuffle）在「图片宽/高不能被块宽/块高整除」时，
**在数学上无法无损可逆**：源块 16×16 有 256 个像素，而目标块可能只有 1×1 一个像素位置，
256 个像素塞不进 1 个槽，必然丢信息。

原版实现没有拒绝这类参数，而是静默产出了永久损坏、**无法解密还原**的图片
（实测 72 种「尺寸 × 块大小」组合中，43 种会毁图）。

本版本已在 JS 侧（`app.js` 的 `getInvalidBlockSizeReason`）拦截这类参数并给出提示，
因此**不会再产生坏图**。但这是**止损，不是修复** —— 该操作本身不可能无损。

如果你需要「任意块大小」，唯一的正解是改用像素级的**吉尔伯特曲线**或**最速混淆**。

### 视频模块需要 WebGL2

视频解密只有一条基于 WebGL2 的 GPU 渲染路径，不支持时会提示
「浏览器不支持 WebGL2，无法使用GPU加速」。图片模块有五级降级管线，不受影响。

---

## 五、修改代码后请注意

- **不要修改** `js/fastest-obfuscation.js` —— 它是从小程序端逐字节移植的，
  改动会破坏与该端的数据兼容性
- **不要修改** `wasm/` 下的文件 —— 除非你能重新编译对应的 Rust 源码
- 改完 CSS/JS 后，建议把 `index.html` 里资源引用的 `?v=` 版本号一并更新，
  否则浏览器可能继续用缓存里的旧文件
