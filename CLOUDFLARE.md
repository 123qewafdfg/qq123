# Cloudflare Workers 部署说明

这个目录是 `123qewafdfg/qq123` 的 Cloudflare Workers 静态资源部署版本。

## Cloudflare 设置

- Production branch: `main`
- Build command: 留空
- Deploy command: `npx wrangler deploy`
- Root directory: `/`
- Worker name: `yuan`

## 为什么需要这些文件

- `_headers`：让 Cloudflare 正确返回 `.wasm` 的 `application/wasm`，同时给静态资源设置缓存。
- 不使用 `_redirects`：Wrangler 会把 `/* /index.html 200` 判定为无限循环，导致部署失败。

## 推送

```powershell
git push origin main
```

如果 Cloudflare 之前绑定的是 `master`，请在 Workers 项目里改成 `main`，或者重新连接 `123qewafdfg/qq123`。
