# Microsoft Store Package (MSIX) 构建指南

本项目已配置为可以打包为 MSIX 包发布到 Microsoft 应用商店。

## 前置要求

1. Windows 10/11 开发环境
2. 安装 Windows SDK (包含 makeappx.exe)
3. 证书签名工具 (signtool.exe)
4. Microsoft Store 开发者账号

## 准备资源文件

正式构建前，请在项目根目录准备 `Assets` 目录，并提供以下真实图片资源：

- `StoreLogo.png`（50x50）
- `Square44x44Logo.png`（44x44）
- `Square150x150Logo.png`（150x150）
- `Wide310x150Logo.png`（310x150）
- `SplashScreen.png`（620x300）

> 正式发布不要使用占位图标。
> 构建脚本现在只会在你显式传入 `--allow-placeholder-assets` 时，才在 `msix_output/Assets` 中生成开发占位图标，避免把占位资源写回仓库。

## 构建步骤

### 方式 1: 使用脚本自动构建 (推荐)

```powershell
# 使用真实资源构建
python build_msix.py
```

仅在本地开发验证时，可以显式允许生成占位图标：

```powershell
python build_msix.py --allow-placeholder-assets
```

### 方式 2: 手动构建

1. 确保已构建可执行文件：
```powershell
python build.py --name sanguosha
```

2. 创建 `Assets` 文件夹并添加真实图标

3. 打包为 MSIX：
```powershell
# 使用 makeappx
& "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\makeappx.exe" pack /d dist\sanguosha /p sanguosha.msix /o
```

4. 签名 (需要证书，推荐通过环境变量传递密码)：
```powershell
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR((Read-Host "证书密码" -AsSecureString))
$env:SANGUOSHA_MSIX_CERT_PASSWORD = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
python build_msix.py --sign --cert certificate.pfx --password-env SANGUOSHA_MSIX_CERT_PASSWORD
Remove-Item Env:SANGUOSHA_MSIX_CERT_PASSWORD
```

## 发布到 Microsoft Store

1. 访问 [Microsoft Partner Center](https://partner.microsoft.com)
2. 创建新的应用提交
3. 上传 MSIX 包
4. 填写应用信息（描述、截图、年龄分级等）
5. 提交审核

## 注意事项

- 应用需要通过 Windows App Certification Kit (WACK) 测试
- 确保遵守 Microsoft Store 政策
- 需要准备隐私政策链接
- 应用名称需要唯一
