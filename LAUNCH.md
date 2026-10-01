# 从预览到正式上线

版本：2026-10-01。当前交付是已测试的本地预览和源码，没有创建远程仓库、购买域名、修改 DNS 或上线。账号授权和付款都由你在官方网站完成，不要把密码、验证码或 access token 发进聊天。

## 第 1 步：创建专门的网站仓库

登录 `enfjp`，打开 https://github.com/new 。Owner 选择 enfjp；Repository name 填 `enfjp.github.io`（使用小写）；Description 可填 `Personal website — research and photography`；Visibility 选择 Public；勾选 Add a README file；点击 Create repository。

GitHub 的用户主页仓库名需要对应 `<user>.github.io`；GitHub Free 的 Pages 可使用公开仓库。[1][2]

创建好以后只需提供仓库网页链接，不要分享登录信息。若名称已存在，先检查现有仓库，不要覆盖或删除它。

## 第 2 步：上传文件

解压 `enfjp-website-v1.1.zip`，打开里面的 `enfjp-website` 文件夹。进入新仓库，点击 `Add file → Upload files`。把该文件夹内部的文件及目录上传，不要上传压缩包本身，不要多套一层目录。根目录必须能看到 `docs`、`content`、`assets`、`tools`、`README.md` 等。

初始版本文件数量低于 GitHub 每次上传 100 个文件的限制，单文件也低于浏览器上传限制。以后增加大量照片时需分批上传或使用 Git。[3]

这一步上传的默认版本没有原始照片、个人邮箱或私人文稿，但仓库中的所有文件仍会公开。不要另行混入原图、私人 CV、学籍文件、未获准公开的稿件等。`noindex` 只向搜索引擎表达请求，不提供保密能力。

提交说明填写 `Add initial personal website`，提交到 main。

## 第 3 步：启用免费网址

打开仓库 `Settings → Pages`。在 Build and deployment 设置：

```text
Source: Deploy from a branch
Branch: main
Folder: /docs
```

点击 Save。等待本次 Pages 工作流结束后，以 Settings → Pages 页面显示的网址为准。预期用户站点地址是 `https://enfjp.github.io/`，但未出现成功部署前不能视为已上线。[2][4]

初次选择 `/docs` 不是 `/(root)`，因为首页位于 `docs/index.html`。Source 暂时不要选 GitHub Actions；自动构建是后面的可选维护步骤。

遇到 404，先检查 main 分支是否确实有 `docs/index.html`，再看 Actions 中 Pages 工作流是否完成。不要立刻反复购买域名或删除仓库。

## 第 4 步：补足可公开的内容

第一批建议选择 12–20 张自己拍摄、愿意公开的照片，至少包括一张适合宽幅展示的封面；每个系列先少放、认真排序。原文件通过聊天交付给设计流程即可，不要直接作为网站公开素材上传 GitHub。

还需确定公开邮箱、Scholar 链接、公开 CV 和准备展示的其他论文。CV 不应含住宅地址、生日、签名、证件信息或不打算公开的电话号码。明确每篇论文的最终题目、作者顺序、会议/年份、录用类别和公开链接。不从聊天草稿猜测录用状态。

替换 `content/site.json`、`content/research.json`、`content/photography.json`，用导入脚本准备网页照片，再重新生成 docs。检查所有照片说明和色彩，尤其是竖图、大幅横图、动物眼睛、地平线等不能被封面裁切破坏的位置。

## 第 5 步：域名确认与付款

先通过免费网址验收再买域名。可考虑 `jipengli.com`，也可考虑 `jipengli.studio`；这些只是命名候选，不是已确认可注册的域名。不要把域名跟当前学校绑定。

可从 Cloudflare Registrar 查询，地址是 https://www.cloudflare.com/products/registrar/ 。该服务按注册局及 ICANN 价格收费；具体域名的可注册状态、首年价、续费价和最终税费以结账页面为准。[5]

付款前查看正常续费价格、是否 premium 域名、自动续费状态、注册信息准确性。不要额外购买与当前静态站无关的主机、企业套餐或建站订阅。必须用你自己的注册商账号购买与持有域名。

## 第 6 步：验证域名，再绑定网站

先在 GitHub 个人账号设置中打开 Pages → Add a domain。这里是个人 Settings，不是仓库 Settings。填写你已购买的域名，按界面提供的名称和值，在域名 DNS 中添加 TXT 记录，然后点击 Verify。TXT 验证值由 GitHub 生成，不要自行编造；验证完成后保留该记录。[6]

然后进入网站仓库 Settings → Pages，在 Custom domain 中保存正式域名，例如你实际持有的 `jipengli.com`。再配置 DNS，根域名 A 记录如下，www 使用 CNAME。以下 IP 和做法来自 GitHub 官方文档；操作时再次核对官方记录。[7]

```text
A      @     185.199.108.153
A      @     185.199.109.153
A      @     185.199.110.153
A      @     185.199.111.153
CNAME  www   enfjp.github.io
```

www 的 CNAME 目标不含 `https://`，不含路径。初次验收先使用普通 DNS 解析，不额外引入代理层；这是一项减少排错变量的部署选择。不要新建 `*` 通配符记录。不要删除现有 MX、TXT 或邮件服务记录；只处理与此次网页目标冲突的记录。新域名不会自动具备邮箱。

DNS 生效和 HTTPS 证书准备可能需要等待。官方文档提示 DNS 传播、HTTPS 选项可用各可能最多约 24 小时，不应承诺立即完成。证书可用后勾选 Enforce HTTPS，并确认 `www` 与不带 `www` 的版本重定向到统一网址。[7][8]

把 `content/site.json` 中的 `site_url` 改成正式 HTTPS 网址，更新 `updated`，并保留 GitHub 创建的 CNAME 配置。本构建脚本不会删除 docs 内已有的 CNAME，但绑定域名仍须在 GitHub 设置完成；仅写 CNAME 文件不代表已绑定。

## 第 7 步：正式发布验收

全部公开资料确认后，把 `preview` 从 true 改为 false。运行：

```sh
python3 tools/build.py --release
python3 tools/check_site.py
```

再次上传更新后的 content/assets/docs（或启用后述自动构建）。确认预览横条消失，页面不再包含 `noindex`，robots.txt 允许抓取，sitemap.xml 列出正式网址。

在真实手机和桌面浏览器上检查：首页、科研入口、每条论文链接、邮箱、Scholar、CV、摄影系列、竖图/横图、左右键、Esc、触摸浏览、404 页面、HTTPS 和 www 重定向。查看网页分享预览时，当前实现包含标题与描述；照片定稿后可以再加社交分享图。

最后再把主页链接加入邮件签名、公开简历、Scholar 等账号。搜索引擎何时索引、如何排名不由本项目保证。

## 后续维护：两种模式不要混用

第一次使用 branch deployment：修改 content 或 assets 后，运行 build.py 和 check_site.py，再把更新后的 docs 上传。仅改 JSON 不会自动改变已发布网页。

后续要自动构建：在 GitHub 使用 Add file → Create new file，文件名填 `.github/workflows/pages.yml`，内容复制 `automation/pages.yml`。把 Pages 的 Source 改为 GitHub Actions，运行该工作流。完成一次成功部署后，每次向 main 提交内容和网页图片，就会重新构建并部署，不必在本机生成 docs。[4][9]

自动化工作流未在用户远程仓库运行过；第一次运行仍需检查 GitHub 授权、Pages 设置和日志。它不会上传原始照片，也不会自动转换新图，图片应先经过网页导出。

长期保留域名自动续费、GitHub 账号恢复手段、源码和原始照片的独立备份。大照片库增长后再讨论独立图片存储，不在第一版增加付费组件。GitHub Pages 发布站点有 1 GB 上限和每月 100 GB 软带宽限制，当前不应把它当无限原图仓库。[10]

## 官方来源

[1] https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages

[2] https://docs.github.com/articles/creating-project-pages-manually

[3] https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository

[4] https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site

[5] https://developers.cloudflare.com/registrar/

[6] https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages

[7] https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site

[8] https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https

[9] https://github.com/actions/starter-workflows/blob/main/pages/static.yml （读取时 SHA：ac6b8077d460266559b43a52d1bde2e0d6922b6d）

[10] https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
