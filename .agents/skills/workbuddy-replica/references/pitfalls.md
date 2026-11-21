# 常见坑与修复

| 症状 | 真正原因 | 修复 |
|---|---|---|
| 顶层页面只有“加载中...” | 内容在 iframe 里 | 先列 frames，保存子页面源码 |
| 截图/打印丢内容 | 默认样式写了 `opacity: 0` | 改为 JS 主动加 `.js-reveal`，补超时兜底与打印恢复 |
| `.js` 已加但主脚本报错，正文全空 | 隐藏由全局 `.js` 门控，观察器未执行 | 只在 JS 选中元素后加 `.js-reveal`，`load` 后 2.5s 强制可见 |
| 减弱动效下锚点仍平滑滚动 | 只改了 `animation/transition`，没复位 `scroll-behavior` | reduce 块加 `html{scroll-behavior:auto}` |
| 打印时标题变成蓝块 | `background-clip:text` 丢失文字色 | 打印样式恢复纯色文字，关闭装饰背景 |
| 窄屏时间线圆点拉长 | `position: static` 改变了 `::after` 的包含块 | 改为 `position: relative; top:0; left:0` |
| 375px 表格被裁 | 五列硬塞进窄容器 | 560px 以下转卡片，保留全部字段 |
| 页面横向滚动 | 某个子元素超宽 | 用逐元素 `right > clientWidth` 找元素，不要用 `overflow-x:hidden` 掩盖 |
| `scrollWidth` 显示不溢出但页面仍被裁 | `overflow-x:hidden` 传播到视口，指标失真 | 改用逐元素右边界检查 |
| 320px 长英文/公式溢出 | 只写了 `text-wrap: balance` | 加 `overflow-wrap:anywhere`、`word-break:break-word`、`min-width:0` |
| 轨迹飞到城市另一头 | 增量坐标顺序解反 | 用终点与 `endPoint` 对比，误差应在米级 |
| 地图南北端偏移 | 站点与瓦片投影不一致 | 统一 Web Mercator 公式与缩放级别 |
| 同 Seed 仍不同 | 只固定了噪声，粒子仍用 `Math.random()` | 用 seeded PRNG 接管全部随机流 |
| 换设备后同 Seed 仍不同 | DPR 或 resize 历史不同 | 确定性验收加“同 DPR、同 resize 历史”前提 |
| resize 后画面重置 | 监听里调用了 `regenerate()` | 快照 + 粒子坐标缩放，不重新生成 |
| resize 后粒子纵向拉伸 | y 比例写反成 `oldH/height` | 用 `sx=width/oldW`、`sy=height/oldH` |
| resize 后出现横贯全屏长条 | 只缩放了 `x/y`，没缩放 `prevX/prevY` | 同时缩放上一帧坐标 |
| resize 后黑底/透明 | 改 `canvas.width` 重置了上下文状态 | 重新 `setTransform(dpr,...)`、设线宽/线帽、先铺背景 |
| 导出图模糊 | 只按 CSS 像素绘制 | DPR 上限 2，按物理像素设置画布 |
| 同 Seed PNG 字节不同 | PNG 元数据/编码器差异 | 比较像素哈希，不比较文件字节 |
| 暂停后画面仍变化 | 动画循环未真正停，或导出前多跑一帧 | 暂停后停止 update/draw，导出前先停一帧 |
| 320px 标题被裁 | `white-space: nowrap` 或长 token 不可断 | 改 `text-wrap: balance` + `overflow-wrap:anywhere` |
| 320px 行首出现孤立“·” | flex 换行把分隔符推到下一行 | 480px 以下改竖排网格，隐藏分隔符 |
| 图表 ID 重复 | 桌面/移动两套 SVG 用了同一组 ID | 加 `D`/`M` 后缀 |
| 文章图表在移动端挤成一团 | 桌面图表直接缩放 | 单独做移动 SVG，限宽 440px |
| 动效在低性能设备上卡 | 大面积 `filter`/`backdrop-filter` | 降级为纯色/透明度过渡 |
| 空格键暂停失效或劫持按钮 | 全局 keydown 没判断焦点 | 焦点在 `button`/`a`/`input` 时不处理 |
| 无 JS 时画布页空白 | 只有 canvas，没有静态兜底 | 提供静态图或 `<noscript>` 说明 |
| 相对日期发布即过期 | 复刻了“22 小时前” | 冻结为绝对日期，标注快照时间 |
| 站内绝对路径检查误报 | `Path("posts") / "/posts/x.html"` 丢弃左侧 | 以仓库根为基准 `lstrip("/")` 再拼接 |
| `javascript:` 链接被当文件 | 没判断 URL scheme | scheme 非空一律跳过（http/https 需单独判外链） |
| 外链打开后丢失来源 | 缺 `rel="noopener noreferrer"` | 统一 `target="_blank"` + `rel` |
| 首页出现“5 篇/4 条”自相矛盾 | 只改了卡片，漏了 KPI/`--latest`/meta/README | 用 `assets/cases.json` + `sync_site.py --check` |
| OSM 底图未署名 | 只抓瓦片，没保留版权 | 加 `© OpenStreetMap contributors` 与 ODbL 说明 |
| 发布内容泄露金额/行程 | 直接复刻原作数据 | Phase 0 加脱敏清单，发布前逐项核对 |
| 打开链接只看到登录卡片 | 内容在登录墙后面，未登录 | 先由用户本人登录，再在同一会话继续；不要匿名猜内容 |
| 子页面另开标签又要登录 | 新上下文的 Cookie 是空的 | 在已登录的同一浏览器上下文里打开，或从已登录页面内部取 |
| 保存后地图/接口数据全空 | 鉴权 key 与私有接口在静态化后失效 | 换离线底图或本地数据，并在文章写明“已知限制” |
| 复刻页出现真实头像、昵称、账号 | 直接复制了登录后才可见的数据 | 发布前替换为示例值或打码，登录态数据一律脱敏 |
