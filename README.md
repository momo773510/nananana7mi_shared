# 七海娜娜7米 - 微信小程序

本仓库是微信云存储中的文件镜像. 将来可能会将其他代码上传. 数据库将保持私密(但你可以向作者请求导出, 数据本身只是调用Bilibili公共api得到的统计数据).

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
  - [游戏](cloud/data/gamesData.json) 游戏数据. 来源是萌娘百科(复制, 不通过接口)
  - [周边](cloud/data/goodsData.json) 周边页面数据. 包括图片与详情
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

文件的组织与命名还是很混乱的.

如果想要提出建议, 补充信息, 或有版权相关问题, 建议通过Bilibili联系作者(uid). 不嫌麻烦也可以提issue等等.
