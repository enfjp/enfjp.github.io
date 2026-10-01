# Jipeng Li — Research & Photography

第一版设计预览，2026-10-01。代码已生成和测试，但没有从本工作环境发布到线上。当前没有原始摄影作品、公开邮箱、CV 或 Scholar 地址；没有用他人照片填充，也没有写入未经核实的论文录用标注。

## 先看网站

解压后，用浏览器打开 `docs/index.html`。导航使用相对路径，不需要安装依赖才能查看这份静态网站。独立的 `enfjp-site-preview.html` 是全站离线预览，单独随交付提供，不用上传仓库。

当前 `content/site.json` 中 `preview` 为 `true`。每页会显示预览标记，带有 `noindex, nofollow`，robots.txt 请求不爬取。**预览模式不是密码保护：一旦上传公开仓库或开启 Pages，别人仍能访问。不要上传任何私人材料。**

## 最简单的第一次部署

创建公开仓库 `enfjp/enfjp.github.io`，上传本目录内的文件及子目录。在仓库 `Settings → Pages` 选择 `Deploy from a branch`、`main`、`/docs`。第一次部署不需要本地 Python、Node、付费模板或服务器。完整过程见 `LAUNCH.md`。

上传的是文件夹内的内容，不是 ZIP 文件；仓库根目录应直接出现 `docs`、`content`、`assets`、`tools`、`README.md` 等，不能再多套一层 `enfjp-website`。

## 文件结构

```text
content/site.json          姓名、简介、公开联系方式、域名、预览开关
content/research.json      已核实论文的标题、作者、链接和简述
content/photography.json   摄影系列、图片顺序、说明、替代文本
assets/style.css           全站视觉样式
assets/site.js             手机导航、图库、键盘操作、引用复制
assets/favicon.svg         文字站点图标
assets/photos/             之后添加的网页图片，不放原始文件
assets/cv.pdf              之后加入审核过的公开 CV（目前不存在）
tools/build.py             从内容文件生成 docs（Python 3.9+，标准库）
tools/check_site.py        检查站内链接、资源、锚点和基础元数据
tools/add_photo.py         网页图片导出、EXIF 清理、摄影目录更新（需 Pillow）
automation/pages.yml      可选自动部署工作流，默认不执行
docs/                     唯一的网站发布目录，已经生成
DESIGN.md                  设计规范
LAUNCH.md                  部署、域名、上线及维护指南
QA.md                      已执行测试及未测试项目
```

## 修改内容

只修改 `content/*.json` 和 `assets/`，然后重新生成：

```sh
python3 tools/build.py
python3 tools/check_site.py
```

上述命令从项目根目录执行。首次部署只使用已经生成的 `docs`，不需要运行这些命令。手工修改 `docs/*.html` 可以临时生效，但下次构建会被覆盖。

第一次采用 branch deployment 时，修改内容文件不会自动生成 HTML：必须重新构建并上传更新后的 `docs`。后续可以启用 `automation/pages.yml`，让每次提交后自动构建；详见 `LAUNCH.md`。

## 添加照片

先保持原始文件在项目目录外，只将处理后的网页版本放进网站。安装 Pillow 后，运行单张图片导入命令，参数须换成该照片真实的信息：

```sh
python3 -m pip install Pillow
python3 tools/add_photo.py wild /完整路径/项目外的照片.jpg \
  --title "An evening encounter" \
  --alt "A fox standing in grass in evening light" \
  --location "Yellowstone" \
  --year 2026
python3 tools/build.py
python3 tools/check_site.py
```

命令中标题、描述和地点只是填写格式示例，不是已存在的用户作品。导入脚本依次处理 EXIF 方向、将有效的嵌入色彩配置转换为 sRGB、输出长边不超过 900/1600/2400 像素的 WebP，并去掉 EXIF/GPS。小图不会放大。没有色彩配置的图按已是 sRGB 处理；应先从修图软件导出 sRGB JPEG。异常配置会报错，而不是猜测颜色。原图不会复制到仓库。

每张照片必须有标题和描述画面内容的英文 `alt` 文本。`location` 只放你愿意公开的粗略地名，不要写私人地址或敏感野生动物的精确位置。

`cover` 决定系列封面；为空时用该系列第一张图。`photos` 数组顺序决定浏览顺序。系列封面允许裁切，单张照片与全屏查看保持完整构图。

## 上线前

核实内容，补入摄影和公开邮箱，将 `preview` 改为 `false`，更新 `site_url` 和 `updated`，执行：

```sh
python3 tools/build.py --release
python3 tools/check_site.py
```

`--release` 会阻止仍处于预览模式、没有公开邮箱或没有照片的版本发布构建。它不会自动付款、购买域名、推送 GitHub 或审核个人资料的真实性。正式域名仍须在 GitHub Pages 设置中绑定。

## 权利与隐私

本项目没有包含字体文件、他人的照片或付费主题。系统字体由访问者设备提供。没有加入统计脚本、第三方字体请求、登录功能或收集访客信息的表单。代码不设置 cookie；托管服务自身可能保留技术访问记录。

不要因为仓库公开就默认摄影作品使用开源许可。正式作品授权说明由作者决定。GitHub 的公开提交历史也会保留曾经上传的文件；仅从网站页面隐藏材料不等于从仓库历史删除。
