# HandDraft

HandDraft 是一个本地优先的开源文档转手写工具。它可以读取 Markdown、文本和 Word 文档，使用开源或用户上传的字体逐字排版，再输出净纸页面或带桌面环境的拍照效果。

## 功能

- 上传 `.md`、`.markdown`、`.txt`、`.docx`
- `.doc`：本机存在 LibreOffice/soffice 时自动转换，否则提示另存为 `.docx`
- 无需文件也可直接输入文字并实时预览
- 自定义背景只需上传一张包含纸张与周边环境的完整照片
- 原项目实拍白纸、实拍横线、标准横线、笔记纸、报告正文和报告首页模板
- 纯白纸、方格纸以及自定义纸张图片
- 桌面拍照与净纸页面两种输出模式
- 字号、行距、字距、页边距、墨色、轻微起伏等参数
- 多页 PNG、PDF、ZIP 导出
- 上传 `.ttf`、`.otf`、`.ttc` 字体
- 一键安装 OFL 开源字体并保存许可证
- 预留 BYOK 大模型字迹库接口

## 字体与模板来源

应用只把许可证明确的字体加入下载目录：

- Xiaolai：SIL Open Font License 1.1
- LXGW WenKai：SIL Open Font License 1.1
- Google Fonts 中的 ZCOOL KuaiLe、Zhi Mang Xing、Long Cang、Ma Shan Zheng、Liu Jian Mao Cao：SIL Open Font License 1.1

界面只提供日常手写字体与用户上传字体，草书、标题字体和系统楷书不会进入可选列表。应用会优先使用本机导入的参考项目字库；没有本地参考字库时，默认回退到 OFL 授权的 `Xiaolai` 和 `LXGW WenKai`。


## 安装与运行

```powershell
cd E:\zhuanli\handdraft
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn handdraft.main:app --host 127.0.0.1 --port 8017
```

如果 Windows 禁止直接执行 PowerShell 脚本，可以使用：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 -Port 8017
```

打开 `http://127.0.0.1:8017`。

## 分享给朋友

### 同一 Wi-Fi 临时使用

在你的电脑上运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 -HostAddress 0.0.0.0 -Port 8017
```

用 `ipconfig` 查看本机 IPv4 地址，例如 `192.168.1.23`。朋友连接同一
Wi-Fi 后访问 `http://192.168.1.23:8017`。Windows 首次询问防火墙权限时，
只允许“专用网络”即可。

### Docker 或云服务器

```bash
docker build -t handdraft .
docker run --rm -p 8017:8017 handdraft
```

部署到支持 Docker 的云服务后，将平台分配的公网网址发给朋友即可。
当前版本没有账号、访问控制、限流和自动清理；上传文档与生成结果会暂存
在服务器的 `data/jobs`。建议只在可信朋友间临时使用，长期公开部署前应
增加登录、HTTPS、限流和定时清理。

## API Key 安全

- Key 不写进前端源代码
- Key 不保存到 localStorage 或 sessionStorage
- 后端不写盘、不回显完整 Key
- 请求完成后输入框自动清空
- 日志过滤器对疑似密钥打码
- `.env` 已加入 `.gitignore`

## 测试

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
.\.venv\Scripts\python scripts\smoke_test.py
.\.venv\Scripts\python scripts\acceptance_test.py
```

运行 `acceptance_test.py` 前需先启动本地服务。验收范围包括全部内置纸张模板、Markdown、Word、单图自定义实拍模板、两种输出模式、PNG/PDF/ZIP、默认字体和 API Key 打码。

## 开源许可证

HandDraft 源代码采用 MIT License，见 `LICENSE`。字体、照片和图标保留各自
许可证或授权条件，不由 MIT License 重新授权；完整说明见
`THIRD_PARTY_NOTICES.md`。
