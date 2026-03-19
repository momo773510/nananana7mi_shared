# 七海娜娜7米 - 微信小程序

- 本仓库是微信云存储中的文件镜像, 数据库将保持私密(微信云数据库, 不方便导出)但你可以向作者请求导出, 数据本身只是调用Bilibili公共api得到的统计数据.

- 小程序的主体基本上都是AI生成的. 科技改变生活! 整理好之后会将代码开源.

- 作者有实现一个AI七海的想法, 目前处于新建文件夹阶段. 现在的tts,svc技术相对成熟, 实现难度不大; 训练七海风格的AI可能稍显麻烦, 但并非无从下手. 事实上，小程序由于平台特性, 并不适合实现一些复杂功能. 如果寻求AI七海, 弹幕站, 数据查询接口, 那相当于搭建一个类似于laplace.live的巨无霸网站. 当然, 作者有计划将小程序的功能迁移到独立网站中. 这是完全可以做到的, 而且不能说是比较复杂. 不过限于个人能力问题, 这是遥遥无期的...在慢慢迁移的同时, 作者期盼有前后端高手协助实现此愿景. 或者直接做一个.

## 文件结构

小程序的数据来源分为本地与云存储, 本地存储的[文件](local/images)仅包括

- tabbar中item的图片
- userlogo中的鲨鱼鳍与浪花
- 音乐播放旋钮的图片

因为微信小程序对包体大小有要求.

而云存储则包含[数据](cloud/data), [图像](cloud/images)与[音乐](cloud/music):

- 数据: 以json存储的各页面数据
  - [首页](cloud/data/indexData.json) 首页. 有一大堆东西.
  - [关于](cloud/data/aboutData.json) 关于页面
  - [直播日历](cloud/data/calendarData.json) 日历组件的数据. 包括每场直播对应服装的图像, 以及每个月的直播日历图像.
  - [新闻](cloud/data/newsData.json) 新闻页面数据. 包括新闻与经历. 这个很粗糙.
  - [醒目留言](cloud/data/messageData.json) 本来是想做成留言区的, 但是微信不让, 所以留下了这个静态的组件.

其实很多东西都能用数据库存储, 但是一开始没考虑这么多, 可能会慢慢迁移.

- 图像:
  - [应用](cloud/images/app) 应用级别的图像资源, 包括tabbar图标、页面背景图等.
  - [日历](cloud/images/calendar) 直播日历相关的图像, 包括服装图像和月历图像. 包含AI生成, 有的图像没联系上作者.
  - [周边](cloud/images/goods) 周边商品图片, 分为官方周边、航海礼物和虚拟周边.
  - [首页](cloud/images/index) 首页相关图片, 包括头像、图标、背景和[服装详情图](cloud/images/index/detail/).
  - [新闻](cloud/images/news) 新闻页面图片.

- 音乐:
  - [音频](cloud/music) 背景音乐和鲨鱼鳍交互音效.(点击userlogo或者鲨鱼鳍)

- 脚本:
  - [弹幕总结](scripts/弹幕总结) 弹幕下载与AI总结工具

文件的组织与命名还是很混乱的.

## 脚本说明

### 弹幕总结脚本

[summarize_danmukus.py](scripts/弹幕总结/summarize_danmukus.py) 是一个用于下载B站视频弹幕并使用AI进行内容总结的脚本。

**主要功能：**

- 从B站下载指定视频或视频系列的弹幕
- 支持多P视频弹幕合并
- 按密度筛选弹幕，保留高密度时段的弹幕
- 调用AI API对弹幕内容进行智能总结，提取直播中的关键事件
- 支持多轮独立总结并整合，提高总结质量

**配置要求：**

使用前需要配置以下参数：

- `API_BASE_URL`: AI服务商API地址
- `API_MODEL`: 使用的模型名称
- `API_KEY`: API密钥

**使用方式：**

```python
# 对系列视频进行总结
summarize_series_videos(
    mid="",              # B站用户ID
    series_name="",      # 系列名称
    api_key=API_KEY,
    max_pages=60,        # 限制页数
    output_file="summaries.json",
    verify_rounds=2,     # 验证轮数
    enable_format=True,  # 格式规整
)
```

如果想要提出建议, 补充信息, 或有版权相关问题, 建议通过Bilibili联系作者(uid3461578995272151). 不嫌麻烦也可以提issue等等. 欢迎交流!
