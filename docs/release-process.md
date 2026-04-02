# Release Process

本项目采用 **Tag 驱动发布**，以 GitHub Actions 自动构建并发布三平台产物。

## 版本规范

- 版本号遵循语义化版本：`vX.Y.Z`
- 示例：`v4.1.2`
- `CHANGELOG.md` 记录格式使用 `[X.Y.Z]`（不带 `v`）

## 发布触发规则

- 工作流文件：`.github/workflows/release.yml`
- 自动触发：`push` 到 `v*.*.*` 标签
- 手动触发：`workflow_dispatch` 仅用于构建验证，不创建 Release

## 标准发布步骤

1. 确认本地 `main` 最新并通过测试
2. 更新 `CHANGELOG.md`，新增对应版本条目（如 `[4.1.2] - YYYY-MM-DD`）
3. 创建并推送标签：

```bash
git tag v4.1.2
git push origin v4.1.2
```

4. 等待 GitHub Actions `Release` 工作流完成
5. 检查 Release 页面：
   - 标题是否为 `Sanguosha CLI v4.1.2`
   - 是否包含三平台产物
   - 自动生成 Notes 是否正常

## 产物清单

- Windows: `sanguosha-windows-amd64.exe`
- Linux: `sanguosha-linux-amd64`
- macOS: `sanguosha-macos-amd64`

## 常见问题

### 为什么手动触发没有创建 Release？

这是预期行为。当前策略避免非 tag 触发导致错误版本（如 `main`）被发布。

### 什么时候会创建 Release？

仅当推送 `vX.Y.Z` 格式标签时创建。
