# Cloudflare Pages 专用部署说明

这个目录是 `123qewafdfg/qq123` 的 Cloudflare Pages 静态部署版本。

## Cloudflare Pages 设置

- Production branch: `main`
- Framework preset: `None`
- Build command: 留空
- Build output directory: `/`
- Root directory: `/`

## 为什么需要这些文件

- `_headers`：让 Cloudflare 正确返回 `.wasm` 的 `application/wasm`，同时给静态资源设置缓存。
- `_redirects`：让直接访问任意路径时回到 `index.html`，避免 Pages 返回 404。

## 推送

```powershell
git push origin main
```

如果 Cloudflare 之前绑定的是 `master`，请在 Cloudflare Pages 项目里改成 `main`，或者重新连接 `123qewafdfg/qq123`。
