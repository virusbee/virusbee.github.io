# 首页与 README 同步

## 单一真源

期号、slug、标题、日期、规模、摘要统一写在 `assets/cases.json`。新增一期时先改这个文件，再同步首页与 README。

## 必须同步的计数点

首页 `index.html`：

- [ ] Hero 文案“目前是第 N 篇”。
- [ ] `Total Logs` 的 `data-target` 与显示值。
- [ ] 终端提示 `--latest <strong>N</strong>`。
- [ ] `Latest` 日期与说明。
- [ ] `Categories` 数量与说明（当前单主题为 1）。
- [ ] 饼图 `aria-label`、`<title>`、图例数量。
- [ ] 分类计数 `N 条`。
- [ ] 新卡片：编号、标题（关键词用 `<mark>`）、日期、摘要、链接。
- [ ] 卡片按最新在前排序。
- [ ] 页脚“共 N 篇构建日志”。
- [ ] `<meta name="description">` 的篇数。

README `README.md`：

- [ ] 顶部说明“目前收录 N 篇日志”。
- [ ] 文章列表新增一行。
- [ ] Demo 列表新增一行。

## 不要机械修改的项

- 单分类下饼图 `stroke-dasharray` 恒为满环（当前约 `264 264`，2π×42≈263.9），不需要每期改。
- `Categories` 在单主题阶段恒为 1，只有新增主题时才改。
- 卡片摘要不要复制文章 TL;DR；按“规模 + 难点 + 结果”重写。

## 自动化

在仓库根目录运行：

```bash
python3 .agents/skills/workbuddy-replica/scripts/sync_site.py --check
```

脚本会读取 `assets/cases.json`，核对首页与 README 的计数、日期、slug 对应文件是否存在。加 `--fix` 只修复计数类字段（不下发新卡片、不改文案结构）。

新卡片仍需手工插入，因为卡片包含标题高亮、摘要和排序，自动生成容易破坏版式。插入后重新跑一次 `--check`。
