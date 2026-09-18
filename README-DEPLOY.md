# 小番茄 · 视频+图片合并版 —— 部署包

这是可直接部署的版本。整个目录就是网站根目录，**443 KB**，无需构建步骤。
目录里**只包含运行时会用到的文件**，本地开发工具（预览脚本、二维码生成）都不在里面。

```
qq123-deploy/
├── index.html                  # 主页面
├── tb.ico                      # 网站图标
├── _headers                    # Cloudflare 响应头（含 CSP）
├── wrangler.jsonc              # Cloudflare Workers 部署配置
├── .assetsignore               # 指定哪些文件不上传
├── LICENSE                     # 本项目开源协议
├── THIRD-PARTY-NOTICES.md      # 第三方组件版权声明（MIT 合规要求）
├── README-DEPLOY.md            # 本文件
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

本部署包是纯净的线上产物，**不含本地预览脚本**。
预览脚本备份在开发目录 `../_audit/serve.py`，把它复制到本目录后运行：

```bash
cp ../_audit/serve.py .        # Windows: copy ..\_audit\serve.py .
python serve.py 8124           # 只在本机看
python serve.py 9191 0.0.0.0   # 允许局域网/手机访问（会打印可用地址）
# 然后打开 http://127.0.0.1:8124/
```

**不要用 `python -m http.server`**——它不返回 `charset=utf-8`，也不读 `_headers`
和 `.assetsignore`，会导致中文乱码、无法在本地验证 CSP，也会把本该排除的文件暴露出来。

> 若直接在 Cloudflare 上测试，则不需要这个脚本。

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

本版本已在**两个层面**拦截：JS 侧（`app.js` 的 `getInvalidBlockSizeReason`）
和 WASM 侧（`check_block_size`）都会拒绝并给出提示，因此**不会再产生坏图**。
但这是**止损，不是修复** —— 该操作本身不可能无损。

如果你需要「任意块大小」，唯一的正解是改用像素级的**吉尔伯特曲线**或**最速混淆**。

### 视频模块需要 WebGL2

视频解密只有一条基于 WebGL2 的 GPU 渲染路径，不支持时会提示
「浏览器不支持 WebGL2，无法使用GPU加速」。图片模块有五级降级管线，不受影响。

---

## 五、性能说明：三种算法都做了优化

`wasm/` 与 `js/fastest-obfuscation.js` 都是优化过的版本。**所有优化都保证输出逐位不变**
（用 810 组 golden 基线 + 30 项逐位对照验证过），不影响任何已有数据，用户无需迁移。

### 1. 吉尔伯特曲线：多轮 O(N) → O(1)

吉尔伯特本质是沿空间填充曲线做循环平移，所以

```
N 轮  ==  单轮（偏移量 = 基础偏移量 × N  mod  总像素数）
```

原版是真的循环了 N 次；本版本只算一次偏移量。

### 2. 分块打乱：置换的 N 次幂

分块打乱每一轮的映射表完全相同，所以「N 轮」就是同一置换的 N 次幂。
用**二进制幂**在置换空间里求出（O(log N) 次复合），最后只对像素做**一次** remap。

### 3. 最速混淆：按行 + uint32 拷贝 + 顺序缓存

原本的瓶颈不在排序（只占 3%），而在像素搬运（97%）—— 原实现按「外层列、内层跨行」
逐像素拷贝，缓存命中率很差。改成按行处理 + `Uint32Array` 整体拷贝（一像素 4 字节 = 一个 32 位字），
并把置换顺序缓存起来跨图片跨轮数复用。

### 实测（800×1416 真实图片，17 张）

| 算法 | 轮数 | 原版 | 本版本 | 加速 |
|---|---|---|---|---|
**吉尔伯特** | 1 | 11.5 ms | 11.4 ms | 持平 |
 | 100 | 125.9 ms | **12.0 ms** | **10.5x** |
**分块打乱** | 1 | 10.2 ms | 7.6 ms | 1.34x |
 | 100 | 189.9 ms | **18.2 ms** | **10.4x** |
**最速混淆** | 1 | 8.5 ms | 2.3 ms | 3.67x |
 | 100 | 800.6 ms | **182.1 ms** | **4.40x** |

**完整链路（解码 PNG → 加密 → 编码 JPEG，100 轮，单张）：**

| 算法 | 原版 | 本版本 |
|---|---|---|
基线（只解码+编码） | 22 ms | 22 ms |
吉尔伯特 | 151 ms | **37 ms** |
分块打乱 | 194 ms | **39 ms** |
最速混淆 | 822 ms | **208 ms** |

> **注意**：轮数增加**不会提升安全性**。吉尔伯特与分块打乱的 N 轮都只是个可快速求出的
> 置换幂，知道「1 轮」就能推出任意轮。增大轮数只增加耗时，不增加保密强度。

---

## 六、修改代码后请注意

- **不要修改** `js/fastest-obfuscation.js` —— 它是从小程序端逐字节移植的，
  改动会破坏与该端的数据兼容性
- **不要随意替换** `wasm/` 下的文件。这里是重新编译过的版本，包含
  「分块打乱拒绝不整除」与「吉尔伯特 O(1) 多轮」两项改动；
  换回原版会同时丢掉这两项
- 改完 CSS/JS 后，建议把 `index.html` 里资源引用的 `?v=` 版本号一并更新，
  否则浏览器可能继续用缓存里的旧文件
