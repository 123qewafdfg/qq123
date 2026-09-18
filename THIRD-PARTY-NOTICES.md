# 第三方组件与许可声明

本项目（小番茄 · 视频+图片合并版）在 `js/` 目录下以源码形式内置了以下第三方库。
这些库的版权归各自作者所有，本项目按其原始许可条款使用。

内置文件本身是未经修改的上游构建产物，因此无法在文件内补充被压缩器移除的版权声明；
本文件即为满足各许可条款「保留版权声明」要求的 N OTICE 文件。

---

## 1. FileSaver.js 2.0.5

- 文件：`js/FileSaver.min.js`
- 上游：https://github.com/eligrey/FileSaver.js
- 许可：MIT License
- 版权：Copyright © 2016 Eli Grey

## 2. JSZip 3.10.1

- 文件：`js/jszip.min.js`
- 上游：https://github.com/Stuk/jszip
- 许可：MIT License 或 GPLv3（双许可）。**本项目选择 MIT 条款。**
- 版权：Copyright © 2009-2016 Stuart Knightley, David Duponchel, Franz Buchinger, António Afonso
- 注：该文件自身已保留上游 `/*! JSZip v3.10.1 ... Dual licenced under the MIT license or GPLv3 ... */`
  声明头，此处再行列出以便查证。
- 内含 pako（MIT License，Copyright © 2014-2017 Vitaly Puzrin, Andrey Tupitsin）

## 3. lottie-player 2.0.12（内含 lottie-web 5.12.2 与 lit 3.1.2）

- 文件：`js/lottie-player.js`
- 上游：https://github.com/LottieFiles/lottie-player
- 许可：MIT License
- 版权：Copyright © LottieFiles.com
- 内含 lottie-web（MIT License，Copyright © 2015 Bodymovin / Hernan Torrisi）
- 内含 lit 3.1.2（BSD-3-Clause License，Copyright © Google LLC）

> **注意**：本项目中引用该库的加载动画已被移除（原引用的 `img/sandy-loading.json` 不存在，
> 导致请求 404），因此 `js/lottie-player.js` 目前**没有被 `index.html` 加载**。
> 该文件保留在仓库中仅作为历史产物，可以安全删除；一旦删除，本节声明也需同步移除。

---

## 关于许可合规的说明

上游的 `js/FileSaver.min.js` 与 `js/lottie-player.js` 是压缩后的构建产物，
其中原有的 MIT 版权声明已被压缩工具移除。MIT 许可要求「在软件的所有副本或实质性部分中
包含上述版权声明和本许可声明」，因此仅保留项目自身的 `LICENSE` 并不足够 —— 本文件用于补足
这一要求。

如果你重新构建或替换这些内置库，请确认新版本是否自带声明头；若无，请在本文件中更新对应条目。
