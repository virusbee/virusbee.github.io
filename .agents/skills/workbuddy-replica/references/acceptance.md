# 验收手册

## 1. 静态检查

在仓库根目录运行：

```bash
python3 .agents/skills/workbuddy-replica/scripts/check_site.py --root .
```

覆盖项：

- 站内链接、锚点、图片、`srcset`、`script[src]`、`link[href]`、`video[poster]` 存在。
- 重复 `id`；`lang`、`title`、`meta description` 存在。
- 图片有 `alt`；装饰 SVG 有 `aria-hidden`。
- 外链使用 `target="_blank"` + `rel="noopener noreferrer"`。
- 跳过 `http/https/mailto/tel/data/blob/javascript` 与协议相对外链。
- 站点根绝对路径 `/posts/x.html` 解析到仓库根，而不是文件系统根。

脚本输出 `file:line`，有错误时退出码为 1。不要用 `assert`，否则 `python -O` 会跳过检查。

## 2. 视口矩阵

至少覆盖七档：

```text
1440 × 900
1024 × 768
768 × 900
656 × 900
560 × 800
375 × 812
320 × 700
```

优先用 CDP `Emulation.setDeviceMetricsOverride` 或 Playwright `page.setViewportSize()`。不要用 `--window-size=375` 直接跑 headless Chrome：部分版本/平台会钳制到最小窗口宽度（常见 500px），得到的是 500px 布局。

iframe 只能作兜底，并且要接受这些代价：Windows/Linux 的纵向滚动条会吃掉约 15px 布局宽度；`file://` 下根绝对路径会 404，必须起本地服务器；父页面与 iframe 的执行上下文不同，测量要在 iframe 内跑；iframe 不模拟 `devicePixelRatio`、`pointer: coarse`、`visualViewport`、移动端 `dvh`。

每档都测：

```js
({
  vw: document.documentElement.clientWidth,
  scrollW: document.documentElement.scrollWidth,
  overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth
})
```

`scrollWidth` 会被 `overflow-x:hidden` 欺骗：body 的 overflow 可能传播到视口，使 `scrollWidth` 恒等于可视宽度。必须补逐元素检查：

```js
[...document.querySelectorAll('body *')]
  .filter(el => {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.right > document.documentElement.clientWidth + 0.5;
  })
  .slice(0, 20)
  .map(el => ({ tag: el.tagName, cls: el.className, right: el.getBoundingClientRect().right }))
```

注意：抽屉、弹窗、轮播的“屏外待入场”元素可能被误报；给它们加 `data-audit-ignore`，脚本里过滤，而不是直接放宽阈值。

## 3. 功能验收

按案例类型逐项过：

- **报告：** 合计、占比、涨跌符号、双语切换、打印。
- **时间线：** 条目总数、分组数、来源数、外链可点、无 JS 可见、相对日期已冻结。
- **地图：** 站点数、轨迹段数、拖动缩放、弹窗边界、键盘、重置、OSM 署名。
- **画布：** Seed 复现、换 Seed 变化、暂停、导出、DPR2、resize 保留画面、无 JS 静帧兜底。
- **信息流：** 分类计数、KPI 数字、滚动入场、减弱动效。

## 4. 控制台与网络

- Console 无 error。
- Network 无 404、无失败请求。
- 复刻页除文档本身外，最好零外部请求。
- 文章图片全部 `complete && naturalWidth > 0`。

## 5. 打印

- 打印预览里所有正文可见，不被 `opacity: 0` 或动画藏住。
- 渐变标题恢复纯色，不出现蓝色/黑色色块。
- 表格、图表、卡片不被拦腰截断。
- 浮动操作栏、导航、装饰背景隐藏。

## 6. 性能

- Canvas 在 1440×900 @ DPR2 下以 rAF 实测为准，目标约 60fps；不要用固定 sleep 估算。
- 导出尺寸按画布实际 CSS 尺寸 × DPR 计算；4K 屏 × DPR2 可能超过 iOS Safari 单画布约 16,777,216 px 的上限，导出前限面积并 `try/catch` 降级。
- 首屏图片不过大；文章总大小可控。
- 不做无意义的 `requestAnimationFrame` 常驻循环。

## 7. Definition of Done

### 复刻页

- [ ] 可独立打开，无构建步骤，无外部依赖（或依赖已内嵌）。
- [ ] 内容、数据、链接、免责声明完整，无编造；发布内容已脱敏。
- [ ] 不含 Cookie、Token、真实账号、真实头像与昵称；登录后才可见的数据已替换为示例值。
- [ ] 1440/1024/768/656/560/375/320 无横向溢出。
- [ ] 键盘可完成主要操作，焦点可见。
- [ ] `prefers-reduced-motion` 下内容可见、动效可用，`scroll-behavior` 已复位。
- [ ] 无 JS 时正文仍可读；Canvas 页有静态图兜底。
- [ ] 打印不丢内容、不出现色块。
- [ ] Console 无 error，Network 无 404。
- [ ] 画布/地图/表格等核心功能通过专项验收。

### 文章

- [ ] 标题、slug、Build Log 编号、日期正确。
- [ ] Hero、TL;DR、8 个章节、验收表、复盘、CTA 完整。
- [ ] 图片全部加载，图表有标题/描述，移动端可读。
- [ ] 代码片段能说明问题，不是整文件搬运。
- [ ] 站内链接、锚点、图片引用全部有效。
- [ ] 没有重复 ID。
- [ ] 320px 下标题正常换行，无裁切。

### 首页与 README

- [ ] 新卡片按最新在前插入。
- [ ] KPI、`--latest`、饼图、分类计数、页脚、meta、README 全部同步。
- [ ] 首页在 375/320 下无溢出。
- [ ] 所有站内链接可跳转。

### 交付

- [ ] 临时测试文件已清理。
- [ ] 本地服务器已停止。
- [ ] `git status` 中改动清晰可见。
- [ ] 未经明确要求，不 commit、不 push。
