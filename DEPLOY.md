# 部署说明

这是从 `wj` 单独整理出来的线上部署版静态站点。

直接把本目录内容上传到服务器网站根目录即可：

- `index.html`
- `css/`
- `js/`
- `wasm/`
- `favicon.ico`

要求：

- 必须通过 HTTP/HTTPS 访问，不要用 `file://` 打开。
- 服务器需要正确返回 `.wasm` 文件。推荐 MIME：
  - `application/wasm`
- 如果部署到子目录，保持 `index.html`、`js/`、`css/`、`wasm/` 的相对位置不变。

本地测试命令：

```powershell
python -m http.server 8125 --bind 0.0.0.0
```

然后访问：

```text
http://localhost:8125/
```
