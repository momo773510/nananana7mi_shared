import requests
import xml.etree.ElementTree as ET
from openai import OpenAI
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time
import os


# ==================== API 配置 ====================

# AI 服务商配置
API_BASE_URL = " "
API_MODEL = " "
API_KEY = " "  # 默认API Key


# B站Cookie配置（用于弹幕下载，解决412错误）
# 从浏览器登录B站后，按F12打开开发者工具 -> Application -> Cookies -> bilibili.com
# 复制 SESSDATA 的值填入下方（只需要SESSDATA的值，不需要整个cookie字符串）
BILIBILI_SESSDATA = ""  # 例如："xx%xxxx-xx%xxxx-xx%xxxx"

# 七海相关资料文件路径
NANA7MI_PROFILE_FILE = ".txt"
NANA7MI_PROFILE_DEFAULT = "七海Nana7mi是Bilibili旗下VirtuaReal企划的虚拟主播。"


# ==================== Prompt 配置 ====================

# 总结格式样例
SUMMARY_FORMAT_EXAMPLE = """
"""
# 总结要求
SUMMARY_REQUIREMENTS = """
"""

# System Prompt - 总结弹幕
SYSTEM_PROMPT_SUMMARIZE = """你是一个专业的直播内容分析助手，擅长从弹幕内容中提取和总结直播的关键事件。你需要总结的是Bilibili旗下VirtuaReal企划的虚拟主播七海Nana7mi的一场直播弹幕记录。
"""

# System Prompt - 整合总结
SYSTEM_PROMPT_MERGE = """你是一个专业的直播内容分析助手，擅长从弹幕内容中提取和总结直播的关键事件。你需要总结的是Bilibili旗下VirtuaReal企划的虚拟主播七海Nana7mi的一场直播弹幕记录。
"""

# System Prompt - 格式规整
SYSTEM_PROMPT_FORMAT = """你是一个文本格式整理助手。你的任务是将输入的文本进行格式规整，不改变内容含义，只调整格式。
"""

# 整合总结的额外指令
MERGE_INSTRUCTIONS = """请整合以上多轮总结，生成最终版本：
1. 合并所有轮次中提到的事件，去除重复内容
2. 保留每个事件的完整细节，如果不同轮次对同一事件有不同描述，选择更详细准确的版本
3. 并非对多次总结的内容进行再次总结，而是把多次总结的内容拼凑成细节更多更完整的总结
4. 按时间顺序排列事件
5. 确保格式统一、层次清晰"""

# 格式规整要求
FORMAT_REQUIREMENTS = """
1. 保持原有内容不变，只调整格式。不要添加或删除任何实质内容
2. 确保格式统一、层次清晰
3. 不要出现markdown语法，输出纯文本
4. 保持事件按时间顺序排列
5. 确保每个事件的标题格式一致，如"(1) 事件标题"、"(2) 事件标题"等
6. 确保子项目使用统一的缩进和符号（如"-"）"""


# ==================== 工具函数 ====================

def load_nana7mi_profile() -> str:
    """读取七海相关资料文件"""
    try:
        with open(NANA7MI_PROFILE_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return NANA7MI_PROFILE_DEFAULT

def get_openai_client(api_key: str | None = None) -> OpenAI:
    """获取OpenAI客户端"""
    return OpenAI(
        api_key=api_key or API_KEY,
        base_url=API_BASE_URL,
    )

def summarize_danmaku(title: str, danmaku_content: str, api_key: str | None = None) -> str:
    """调用API总结直播内容"""
    
    client = get_openai_client(api_key)
    
    # 加载七海相关资料
    nana7mi_profile = load_nana7mi_profile()
    
    user_prompt = f"""以下是直播内容：
直播标题：{title}

弹幕内容（格式为"时间秒数: 弹幕内容"）：
{danmaku_content}
以下是相关资料：
{nana7mi_profile}
请根据弹幕内容，总结直播中的主要事件。弹幕密度较高的地方应该是事件发生的高概率时间点。参考以下格式：
{SUMMARY_FORMAT_EXAMPLE}

总结要求：
{SUMMARY_REQUIREMENTS}
"""

    response = client.chat.completions.create(
        model=API_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_SUMMARIZE},
            {"role": "user", "content": user_prompt}
        ],
    )
    
    content = response.choices[0].message.content
    return content if content else "API返回内容为空"

def merge_summaries(title: str, summaries: list[str], api_key: str | None = None) -> str:
    """整合所有轮次的总结内容
    
    Args:
        title: 直播标题
        summaries: 所有轮次的总结内容列表
        api_key: API密钥
    
    Returns:
        整合后的最终总结
    """
    client = get_openai_client(api_key)
    
    # 加载七海相关资料
    nana7mi_profile = load_nana7mi_profile()
    
    # 构建所有轮次总结的内容
    summaries_text = "\n\n".join([f"=== 第{i+1}轮总结 ===\n{s}" for i, s in enumerate(summaries)])
    
    user_prompt = f"""以下是直播内容：
直播标题：{title}

以下是相关资料：
{nana7mi_profile}

以下是对同一场直播的多轮总结（每轮使用了不同的弹幕样本），请整合这些总结，生成最终版本：
{summaries_text}

参考格式：
{SUMMARY_FORMAT_EXAMPLE}

合并指导：
{MERGE_INSTRUCTIONS}

总结要求：
{SUMMARY_REQUIREMENTS}
"""
    
    response = client.chat.completions.create(
        model=API_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_MERGE},
            {"role": "user", "content": user_prompt}
        ],
    )
    
    content = response.choices[0].message.content
    return content if content else summaries[-1] if summaries else "整合失败"

def format_summary(summary: str, api_key: str | None = None) -> str:
    """格式规整函数：只让大模型对总结内容进行格式规整
    
    Args:
        summary: 待规整的总结内容
        api_key: API密钥
    
    Returns:
        规整后的总结内容
    """
    client = get_openai_client(api_key)
    
    user_prompt = f"""请对以下直播总结内容进行格式规整，要求：

{FORMAT_REQUIREMENTS}

参考格式：
{SUMMARY_FORMAT_EXAMPLE}

待规整的内容：
{summary}
"""
    
    response = client.chat.completions.create(
        model=API_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_FORMAT},
            {"role": "user", "content": user_prompt}
        ],
    )
    
    content = response.choices[0].message.content
    return content if content else summary

def download_danmaku_simple(bvid: str, api_key: str | None = None):
    """简化版弹幕下载"""
    
    # 设置请求头（B站 API 需要）
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com",
    }
    # 添加Cookie（解决412错误）
    if BILIBILI_SESSDATA:
        headers["Cookie"] = f"SESSDATA={BILIBILI_SESSDATA}"
    
    # 1. 获取视频信息
    info_url = "https://api.bilibili.com/x/web-interface/view"
    params = {"bvid": bvid}
    
    response = requests.get(info_url, params=params, headers=headers)
    data = response.json()
    
    if data["code"] != 0:
        print(f"错误: {data['message']}")
        return
    
    cid = data["data"]["cid"]
    title = data["data"]["title"]
    
    print(f"视频: {title}")
    print(f"CID: {cid}")
    
    # 2. 下载弹幕
    danmaku_url = "https://api.bilibili.com/x/v1/dm/list.so"
    params = {"oid": cid}
    
    response = requests.get(danmaku_url, params=params, headers=headers)
    
    if response.status_code == 200:
        # 正确处理编码
        response.encoding = 'utf-8'
        xml_content = response.text
        
        # 保存XML文件
        xml_filename = f"{bvid}_danmaku.xml"
        with open(xml_filename, "w", encoding="utf-8") as f:
            f.write(xml_content)
        print(f"XML已保存到: {xml_filename}")
        
        # 解析XML并转换为JSON
        danmaku_list = parse_danmaku_xml(xml_content)
        
        # 保存TXT文件
        txt_filename = f"{bvid}_danmaku.txt"
        with open(txt_filename, "w", encoding="utf-8") as f:
            for item in danmaku_list:
                f.write(f"{item['time']}: {item['text']}\n")
        print(f"TXT已保存到: {txt_filename}")
        
        print(f"弹幕数量: {len(danmaku_list)}")
        
        # 调用API总结直播内容
        if api_key:
            print("\n正在调用API总结直播内容...")
            danmaku_content = "\n".join([f"{item['time']}: {item['text']}" for item in danmaku_list])
            summary = summarize_danmaku(title, danmaku_content, api_key)
            
            # 保存总结结果
            summary_filename = f"{bvid}_summary.txt"
            with open(summary_filename, "w", encoding="utf-8") as f:
                f.write(f"直播标题：{title}\n\n")
                f.write(summary)
            print(f"总结已保存到: {summary_filename}")
            print("\n=== 直播总结 ===\n")
            print(summary)
    else:
        print(f"下载失败: {response.status_code}")

def filter_danmaku_by_density(danmaku_list: list, max_count: int = 2000, round_index: int = 0) -> list:
    """按密度筛选弹幕（保持密度比例）
    
    Args:
        danmaku_list: 弹幕列表
        max_count: 最大弹幕数量
        round_index: 轮询索引，用于在不同轮询中选取不同的弹幕。
                     通过轮流选取每个小段中的弹幕来实现。
                     例如：round_index=0 选第0、3、6...条，round_index=1 选第1、4、7...条
    
    Returns:
        筛选后的弹幕列表
    """
    if len(danmaku_list) <= max_count:
        return danmaku_list
    
    if not danmaku_list:
        return []
    
    # 按time排序
    danmaku_list.sort(key=lambda x: x["time"])
    
    # 计算视频总时长
    max_time = danmaku_list[-1]["time"]
    if max_time == 0:
        return danmaku_list[:max_count]
    
    # 计算需要分成多少个时间段（桶）
    target_per_bucket = 3
    num_buckets = max_count // target_per_bucket
    if num_buckets < 1:
        num_buckets = 1
    
    # 计算每个桶的时间范围
    bucket_time_size = max_time / num_buckets
    
    # 将弹幕分配到各个桶
    buckets = [[] for _ in range(num_buckets)]
    for item in danmaku_list:
        bucket_idx = min(int(item["time"] / bucket_time_size), num_buckets - 1)
        buckets[bucket_idx].append(item)
    
    # 计算每个桶应该保留的弹幕数量（按比例分配）
    total_danmaku = len(danmaku_list)
    result = []
    
    for bucket in buckets:
        if not bucket:
            continue
        bucket_count = max(1, int(len(bucket) / total_danmaku * max_count))
        bucket_count = min(bucket_count, len(bucket))
        if bucket_count >= len(bucket):
            result.extend(bucket)
        else:
            # 将桶内弹幕分成 bucket_count 个小组，每个小组轮流选取
            # 例如：bucket有10条弹幕，需要选3条，分成3组
            # round_index=0: 选第0、3、6条 (索引0,3,6)
            # round_index=1: 选第1、4、7条 (索引1,4,7)
            # round_index=2: 选第2、5、8条 (索引2,5,8)
            
            group_count = bucket_count  # 分成多少组
            items_per_group = len(bucket) // group_count  # 每组至少有多少条
            remainder = len(bucket) % group_count  # 余数
            
            for i in range(bucket_count):
                # 计算当前组的起始位置
                # 前remainder组有 items_per_group + 1 个元素
                if i < remainder:
                    start = i * (items_per_group + 1)
                    # 在当前组内按 round_index 选择
                    # round_index % (items_per_group + 1) 确保不越界
                    offset = round_index % (items_per_group + 1)
                    idx = start + offset
                    if idx >= start + items_per_group + 1:
                        idx = start  # 如果超出当前组范围，回到组首
                else:
                    start = remainder * (items_per_group + 1) + (i - remainder) * items_per_group
                    offset = round_index % max(1, items_per_group)
                    idx = start + offset
                    if idx >= len(bucket):
                        idx = start
                
                result.append(bucket[idx])
    
    # 如果总数仍超过 max_count，按时间均匀采样（同样使用轮流选取）
    if len(result) > max_count:
        # 将result分成 max_count 组
        group_count = max_count
        items_per_group = len(result) // group_count
        remainder = len(result) % group_count
        
        new_result = []
        for i in range(max_count):
            if i < remainder:
                start = i * (items_per_group + 1)
                offset = round_index % (items_per_group + 1)
                idx = start + offset
                if idx >= start + items_per_group + 1:
                    idx = start
            else:
                start = remainder * (items_per_group + 1) + (i - remainder) * items_per_group
                offset = round_index % max(1, items_per_group)
                idx = start + offset
                if idx >= len(result):
                    idx = start
            
            new_result.append(result[idx])
        result = new_result
    
    result.sort(key=lambda x: x["time"])
    return result


def parse_danmaku_xml(xml_content: str, max_count: int = 2000) -> list:
    """解析弹幕XML并转换为JSON格式（仅保留time和text）"""
    danmaku_list = []
    
    try:
        root = ET.fromstring(xml_content)
        
        for d in root.findall("d"):
            p_attr = d.get("p", "")
            text = d.text or ""
            
            # 解析p属性: 时间,类型,字号,颜色,时间戳,池,用户hash,弹幕id
            parts = p_attr.split(",")
            if len(parts) >= 1:
                danmaku = {
                    "time": int(float(parts[0])),     # 出现时间(秒)，抛弃小数
                    "text": text                        # 弹幕内容
                }
                danmaku_list.append(danmaku)
    except ET.ParseError as e:
        print(f"XML解析错误: {e}")
    
    # 按密度筛选
    result = filter_danmaku_by_density(danmaku_list, max_count)
    if len(danmaku_list) > max_count:
        print(f"原始弹幕数: {len(danmaku_list)}, 筛选后: {len(result)}")
    
    return result

def get_series_bvids(mid: str, series_name: str, max_pages: int = 10) -> list[dict]:
    """
    获取指定系列的视频列表
    
    Args:
        mid: B站用户ID
        series_name: 系列名称
        max_pages: 最多获取的页数
    
    Returns:
        包含视频信息的列表，每个元素包含 bvid, title, created_at(上传时间戳)
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://space.bilibili.com/"
    }
    
    # 步骤1: 获取用户的系列列表
    print(f"正在获取用户 {mid} 的系列列表...")
    series_list_url = "https://api.bilibili.com/x/polymer/web-space/seasons_series_list"
    params = {
        "mid": mid,
        "page_num": 1,
        "page_size": 10
    }
    
    response = requests.get(series_list_url, params=params, headers=headers)
    print(f"请求URL: {response.url}")
    print(f"状态码: {response.status_code}")
    
    data = response.json()
    print(f"API返回code: {data.get('code')}, message: {data.get('message')}")
    
    if data.get("code") != 0:
        raise Exception(f"获取系列列表失败: {data.get('message')}")
    
    # 步骤2: 查找指定名称的系列
    series_list = data.get("data", {}).get("items_lists", {}).get("series_list", [])
    target_series = None
    
    for series in series_list:
        if series.get("meta", {}).get("name") == series_name:
            target_series = series
            break
    
    if not target_series:
        raise Exception(f"未找到名为\"{series_name}\"的系列")
    
    series_id = target_series["meta"]["series_id"]
    print(f"找到系列: {series_name} (ID: {series_id})")
    
    # 步骤3: 分页获取系列中的所有视频
    all_archives = []
    current_page = 1
    page_size = 30
    
    while current_page <= max_pages:
        print(f"正在获取第 {current_page} 页...")
        archives_url = "https://api.bilibili.com/x/series/archives"
        params = {
            "mid": mid,
            "series_id": series_id,
            "pn": current_page,
            "ps": page_size,
            "only_normal": "true",
            "sort": "desc"
        }
        
        response = requests.get(archives_url, params=params, headers=headers)
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"获取系列视频失败（第{current_page}页）: {data.get('message')}")
        
        page_archives = data.get("data", {}).get("archives", [])
        all_archives.extend(page_archives)
        
        # 检查是否还有更多数据：如果返回的视频数少于页大小，说明已经是最后一页
        if len(page_archives) < page_size:
            break
        
        current_page += 1
    
    print(f"共获取 {len(all_archives)} 个视频")
    
    # 步骤4: 提取需要的信息，并获取每个视频的cid
    result = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com",
    }
    if BILIBILI_SESSDATA:
        headers["Cookie"] = f"SESSDATA={BILIBILI_SESSDATA}"
    
    print("正在获取视频cid信息...")
    for i, archive in enumerate(all_archives):
        bvid = archive.get("bvid", "")
        title = archive.get("title", "")
        
        # 获取视频的cid列表
        cids = []
        try:
            info_url = "https://api.bilibili.com/x/web-interface/view"
            params = {"bvid": bvid}
            response = requests.get(info_url, params=params, headers=headers, timeout=10)
            data = response.json()
            if data.get("code") == 0:
                pages = data.get("data", {}).get("pages", [])
                if pages:
                    cids = [page["cid"] for page in pages]
                else:
                    cids = [data.get("data", {}).get("cid", 0)]
            time.sleep(0.3)  # 避免请求过快
        except Exception as e:
            print(f"获取 {title} 的cid失败: {e}")
        
        record = {
            "bvid": bvid,
            "title": title,
            "cids": cids
        }
        result.append(record)
        print(f"  [{i+1}/{len(all_archives)}] {title} - cid: {cids}")
    
    return result


def get_or_load_bvids(mid: str, series_name: str, max_pages: int = 10,
                      bvid_cache_file: str = "bvid.json") -> list[dict]:
    """
    获取系列视频列表（支持持久化缓存）
    
    优先从本地缓存文件读取，如果缓存不存在则调用API获取并保存到缓存文件
    
    Args:
        mid: B站用户ID
        series_name: 系列名称
        max_pages: 最多获取的页数
        bvid_cache_file: BV号缓存文件名，默认为bvid.json
    
    Returns:
        包含视频信息的列表，每个元素包含 bvid, title
    """
    # 尝试从缓存文件读取
    try:
        with open(bvid_cache_file, "r", encoding="utf-8") as f:
            cached_data = json.load(f)
            # 验证缓存数据格式（需要包含bvid, title, cids）
            if isinstance(cached_data, list) and all(
                "bvid" in item and "title" in item and "cids" in item
                for item in cached_data
            ):
                print(f"从缓存文件 {bvid_cache_file} 加载了 {len(cached_data)} 个视频信息")
                return cached_data
            else:
                print("缓存文件格式不正确（缺少cids字段），将重新获取")
    except FileNotFoundError:
        print(f"缓存文件 {bvid_cache_file} 不存在，将从API获取")
    except json.JSONDecodeError:
        print(f"缓存文件 {bvid_cache_file} 格式错误，将从API获取")
    except Exception as e:
        print(f"读取缓存文件失败: {e}，将从API获取")
    
    # 从API获取数据
    print("正在从B站API获取系列视频列表...")
    videos = get_series_bvids(mid, series_name, max_pages)
    
    # 保存到缓存文件
    try:
        with open(bvid_cache_file, "w", encoding="utf-8") as f:
            json.dump(videos, f, ensure_ascii=False, indent=2)
        print(f"已将 {len(videos)} 个视频信息保存到缓存文件 {bvid_cache_file}")
    except Exception as e:
        print(f"保存缓存文件失败: {e}")
    
    return videos


def _process_single_video(video: dict, api_key: str, verify_rounds: int, enable_format: bool,
                           total_count: int, file_lock: Lock,
                           task_id: int = 0) -> dict | None:
    """处理单个视频的辅助函数（用于并发）
    
    Args:
        video: 视频信息字典，包含 bvid 和 title
        api_key: API密钥
        verify_rounds: 验证轮数
        enable_format: 是否格式规整
        total_count: 总视频数
        file_lock: 文件写入锁
        task_id: 任务标识ID（用于日志区分）
    
    Returns:
        处理结果字典，包含 bvid, summary, raw_summaries, cids, title，如果跳过则返回 None
    """
    bvid = video["bvid"]
    title = video["title"]
    log_prefix = f"任务{task_id}"
    
    print(f"[{log_prefix}] 开始处理: {title} (BV号: {bvid})")
    start_time = time.time()
    
    try:
        # 下载弹幕并总结（支持多轮验证和格式规整）
        summary, _, raw_summaries, cids, video_title = download_and_summarize(bvid, api_key, verify_rounds, enable_format, log_prefix)
        
        elapsed = time.time() - start_time
        print(f"[{log_prefix}] 完成 {video_title} - 耗时: {elapsed:.1f}秒")
        
        return {
            "bvid": bvid,
            "title": video_title,
            "summary": summary,
            "raw_summaries": raw_summaries,
            "cids": cids,
            "success": True
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[失败] {title} - 耗时: {elapsed:.1f}秒 - 错误: {e}")
        
        return {
            "bvid": bvid,
            "title": title,
            "summary": f"处理失败: {str(e)}",
            "raw_summaries": [],
            "cids": [],
            "success": False
        }


def summarize_series_videos(mid: str, series_name: str, api_key: str, max_pages: int = 10,
                            output_file: str = "summaries.json", verify_rounds: int = 1,
                            enable_format: bool = True, raw_output_file: str = "raw_summaries.json",
                            enable_concurrent_request: bool = False, max_workers: int = 3):
    """
    获取指定系列的所有视频，对每个视频进行总结，并保存为单个JSON文件
    
    Args:
        mid: B站用户ID
        series_name: 系列名称
        api_key: 硅基流动API Key
        max_pages: 最多获取的页数
        output_file: 输出JSON文件名（JSON Lines格式，适合微信云开发导入）
        verify_rounds: 验证轮数，默认为1（只进行一次总结）。如果大于1，会进行多轮验证
        enable_format: 是否在最后进行格式规整，默认为True
        raw_output_file: 原始总结输出文件名（保存每轮的原始总结）
        enable_concurrent_request: 是否启用并发请求，默认为False
        max_workers: 并发请求的最大工作线程数，默认为3
    """
    # 获取系列视频列表（支持持久化缓存）
    videos = get_or_load_bvids(mid, series_name, max_pages)
    
    # 读取已存在的cid（用于跳过已处理的视频）
    existing_cids = set()
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        # 从 _cids 字段读取已处理的 cid
                        if "_cids" in record:
                            for cid in record["_cids"]:
                                existing_cids.add(cid)
                    except json.JSONDecodeError:
                        pass
        if existing_cids:
            print(f"已存在 {len(existing_cids)} 个已处理的cid记录，将跳过包含这些cid的视频")
    except FileNotFoundError:
        pass
    
    # 过滤出需要处理的视频（使用缓存中的cids判断）
    videos_to_process = []
    for v in videos:
        cids = v.get("cids", [])
        # 检查是否有任何一个cid已被处理过
        if not any(cid in existing_cids for cid in cids):
            videos_to_process.append(v)
        else:
            print(f"跳过已处理: {v['title']} (BV号: {v['bvid']})")
    
    print(f"待处理视频数: {len(videos_to_process)}/{len(videos)}")
    
    if not videos_to_process:
        print("没有需要处理的视频")
        return
    
    # 文件写入锁（用于并发写入）
    file_lock = Lock()
    
    # 统计变量
    success_count = 0
    fail_count = 0
    total_start_time = time.time()
    
    if enable_concurrent_request:
        # 并发处理模式
        print(f"\n=== 启用并发处理模式，最大并发数: {max_workers} ===\n")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务，为每个任务分配唯一ID
            future_to_video = {
                executor.submit(
                    _process_single_video,
                    video, api_key, verify_rounds, enable_format,
                    len(videos), file_lock, idx + 1
                ): video for idx, video in enumerate(videos_to_process)
            }
            
            # 打开文件，以追加模式写入JSON Lines格式
            with open(output_file, "a", encoding="utf-8") as f, \
                 open(raw_output_file, "a", encoding="utf-8") as raw_f:
                
                # 按完成顺序处理结果
                for future in as_completed(future_to_video):
                    result = future.result()
                    
                    if result is None:
                        continue
                    
                    bvid = result["bvid"]
                    
                    # 使用锁保证线程安全的文件写入
                    with file_lock:
                        # 写入总结结果（包含所有字段）
                        output_result = {
                            "_id": bvid,
                            "_cids": result["cids"],
                            "raw_summaries": result["raw_summaries"],
                            "summary": result["summary"],
                            "title": result["title"]
                        }
                        f.write(json.dumps(output_result, ensure_ascii=False) + "\n")
                        f.flush()
                        
                        # 写入原始总结（保留原格式兼容）
                        raw_result = {
                            "_id": bvid,
                            "raw_summaries": result["raw_summaries"]
                        }
                        raw_f.write(json.dumps(raw_result, ensure_ascii=False) + "\n")
                        raw_f.flush()
                    
                    if result["success"]:
                        success_count += 1
                    else:
                        fail_count += 1
                    
                    # 打印进度
                    processed = success_count + fail_count
                    print(f"进度: {processed}/{len(videos_to_process)} (成功: {success_count}, 失败: {fail_count})")
    else:
        # 顺序处理模式（原有逻辑）
        print("\n=== 启用顺序处理模式 ===\n")
        
        with open(output_file, "a", encoding="utf-8") as f, \
             open(raw_output_file, "a", encoding="utf-8") as raw_f:
            
            for i, video in enumerate(videos_to_process, 1):
                bvid = video["bvid"]
                log_prefix = f"任务{i}"
                
                print(f"\n[{i}/{len(videos_to_process)}] 处理视频: {video['title']}")
                print(f"  BV号: {bvid}")
                
                try:
                    # 下载弹幕并总结（支持多轮验证和格式规整）
                    summary, _, raw_summaries, cids, video_title = download_and_summarize(bvid, api_key, verify_rounds, enable_format, log_prefix)
                    
                    # 构建符合微信云开发数据库导入格式的记录（包含所有字段）
                    result = {
                        "_id": bvid,
                        "_cids": cids,
                        "raw_summaries": raw_summaries,
                        "summary": summary,
                        "title": video_title
                    }
                    
                    # 写入一行JSON（JSON Lines格式）
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                    print(f"  已写入: {bvid}")
                    
                    # 保存原始总结到raw_summaries.json（保留原格式兼容）
                    raw_result = {
                        "_id": bvid,
                        "raw_summaries": raw_summaries  # 列表，包含每轮的原始总结
                    }
                    raw_f.write(json.dumps(raw_result, ensure_ascii=False) + "\n")
                    print(f"  原始总结已写入: {bvid}")
                    
                    success_count += 1
                    
                except Exception as e:
                    print(f"  处理失败: {e}")
                    # 失败也写入记录，标记错误
                    result = {
                        "_id": bvid,
                        "_cids": [],
                        "raw_summaries": [],
                        "summary": f"处理失败: {str(e)}",
                        "title": video['title']
                    }
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                    fail_count += 1
    
    # 打印统计信息
    total_elapsed = time.time() - total_start_time
    print("\n=== 处理完成 ===")
    print(f"总耗时: {total_elapsed:.1f}秒")
    print(f"成功: {success_count}, 失败: {fail_count}")
    print(f"结果已保存到: {output_file}")
    print(f"原始总结已保存到: {raw_output_file}")


def download_and_summarize(bvid: str, api_key: str, verify_rounds: int = 1, enable_format: bool = True,
                           log_prefix: str = "") -> tuple[str, list, list[str], list[int], str]:
    """下载弹幕并总结（支持多P视频、多轮独立总结和最终整合）
    
    Args:
        bvid: 视频BV号
        api_key: API密钥
        verify_rounds: 总结轮数，默认为1（只进行一次总结）。
                      如果大于1，每轮使用不同的弹幕独立总结，最后整合所有总结。
        enable_format: 是否在最后进行格式规整，默认为True
        log_prefix: 日志前缀（用于并发时区分任务）
    
    Returns:
        (最终总结文本, 弹幕列表, 每轮原始总结列表, cids列表, 视频标题)
    """
    import random
    
    # 随机延迟0-3秒，避免并发请求同时发出触发风控
    time.sleep(random.uniform(2, 4))
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com",
    }
    # 添加Cookie（解决412错误）
    if BILIBILI_SESSDATA:
        headers["Cookie"] = f"SESSDATA={BILIBILI_SESSDATA}"
    
    # 获取视频信息
    info_url = "https://api.bilibili.com/x/web-interface/view"
    params = {"bvid": bvid}
    
    response = requests.get(info_url, params=params, headers=headers)
    data = response.json()
    
    if data["code"] != 0:
        raise Exception(f"获取视频信息失败: {data['message']}")
    
    title = data["data"]["title"]
    
    # 获取所有分P的cid
    pages = data["data"].get("pages", [])
    if not pages:
        # 单P视频
        cids = [data["data"]["cid"]]
        page_durations = [0]
    else:
        # 多P视频，获取所有cid和时长
        cids = [page["cid"] for page in pages]
        page_durations = [page.get("duration", 0) for page in pages]
    
    print(f"[{log_prefix}] 分P数量: {len(cids)}")
    
    # 下载所有分P的弹幕（不筛选，带重试机制）
    all_danmaku_list = []
    max_retries = 3  # 最大重试次数
    retry_delay = 10  # 重试间隔（秒）
    request_delay = 6  # 每次请求间隔（秒），避免触发风控
    
    for i, cid in enumerate(cids):
        # 请求前延迟，避免请求过快触发风控
        if i > 0:
            time.sleep(request_delay)
        danmaku_url = "https://api.bilibili.com/x/v1/dm/list.so"
        params = {"oid": cid}
        
        # 重试机制
        for retry in range(max_retries):
            try:
                response = requests.get(danmaku_url, params=params, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    response.encoding = 'utf-8'
                    xml_content = response.text
                    
                    # 检查是否为有效XML
                    if not xml_content or len(xml_content) < 100:
                        print(f"[{log_prefix}] 警告: 第{i+1}P弹幕内容为空，重试 {retry+1}/{max_retries}")
                        time.sleep(retry_delay)
                        continue
                    
                    # 解析弹幕（不筛选，max_count设为很大）
                    danmaku_list = parse_danmaku_xml(xml_content, max_count=100000)
                    
                    # 多P视频需要调整时间偏移
                    if len(cids) > 1 and i > 0:
                        time_offset = sum(page_durations[:i])
                        for item in danmaku_list:
                            item["time"] += time_offset
                    
                    all_danmaku_list.extend(danmaku_list)
                    print(f"[{log_prefix}] 第{i+1}P弹幕: {len(danmaku_list)}条")
                    break  # 成功，跳出重试循环
                    
                else:
                    print(f"[{log_prefix}] 警告: 第{i+1}P弹幕下载失败 (状态码: {response.status_code})，重试 {retry+1}/{max_retries}")
                    if retry < max_retries - 1:
                        time.sleep(retry_delay)
                        
            except requests.exceptions.RequestException as e:
                print(f"[{log_prefix}] 警告: 第{i+1}P弹幕下载异常 ({e})，重试 {retry+1}/{max_retries}")
                if retry < max_retries - 1:
                    time.sleep(retry_delay)
        else:
            # 所有重试都失败，立即抛出异常跳过该视频
            print(f"[{log_prefix}] 错误: 第{i+1}P弹幕下载失败，跳过该视频")
            raise Exception(f"第{i+1}P弹幕下载失败，跳过该视频")
    
    print(f"[{log_prefix}] 合并后总弹幕: {len(all_danmaku_list)}条")
    
    # 合并后按时间排序
    all_danmaku_list.sort(key=lambda x: x["time"])
    
    # 保存弹幕到danmakus文件夹
    danmaku_dir = "danmakus"
    if not os.path.exists(danmaku_dir):
        os.makedirs(danmaku_dir)
        print(f"[{log_prefix}] 创建弹幕文件夹: {danmaku_dir}")
    
    danmaku_file = os.path.join(danmaku_dir, f"{bvid}.txt")
    if os.path.exists(danmaku_file):
        print(f"[{log_prefix}] 弹幕文件已存在，跳过保存: {danmaku_file}")
    else:
        with open(danmaku_file, "w", encoding="utf-8") as f:
            for item in all_danmaku_list:
                f.write(f"{item['time']}: {item['text']}\n")
        print(f"[{log_prefix}] 弹幕已保存到: {danmaku_file}")
    
    # 记录每轮的原始总结
    raw_summaries = []
    
    # 记录每轮选取的弹幕（用于验证不一致性）
    round_danmaku_sets = []
    
    # 多轮独立总结
    for round_idx in range(verify_rounds):
        # 每轮使用不同的弹幕（通过round_index控制）
        filtered_danmaku = filter_danmaku_by_density(all_danmaku_list, max_count=1500, round_index=round_idx)
        print(f"[{log_prefix}] 第{round_idx + 1}轮筛选后弹幕: {len(filtered_danmaku)}条")
        
        # 记录本轮选取的弹幕ID（用时间+文本作为唯一标识）
        round_danmaku_set = set(f"{item['time']}:{item['text']}" for item in filtered_danmaku)
        round_danmaku_sets.append(round_danmaku_set)
        
        danmaku_content = "\n".join([f"{item['time']}: {item['text']}" for item in filtered_danmaku])
        summary = summarize_danmaku(title, danmaku_content, api_key)
        raw_summaries.append(summary)
        print(f"[{log_prefix}] 第{round_idx + 1}轮总结完成")
    
    # 验证不同轮次的弹幕不一致性
    if verify_rounds > 1:
        print(f"[{log_prefix}] 验证弹幕选取不一致性:")
        for i in range(len(round_danmaku_sets)):
            for j in range(i + 1, len(round_danmaku_sets)):
                overlap = len(round_danmaku_sets[i] & round_danmaku_sets[j])
                total = len(round_danmaku_sets[i])
                overlap_ratio = overlap / total if total > 0 else 0
                print(f"[{log_prefix}]   第{i+1}轮与第{j+1}轮重叠: {overlap}/{total} ({overlap_ratio:.1%})")
    
    # 整合所有轮次的总结
    if verify_rounds > 1:
        print(f"[{log_prefix}] 正在整合所有轮次的总结...")
        final_summary = merge_summaries(title, raw_summaries, api_key)
        print(f"[{log_prefix}] 整合完成")
    else:
        final_summary = raw_summaries[0]
    
    # 最后进行格式规整
    if enable_format:
        print(f"[{log_prefix}] 正在进行格式规整...")
        final_summary = format_summary(final_summary, api_key)
        print(f"[{log_prefix}] 格式规整完成")
    
    return final_summary, filtered_danmaku, raw_summaries, cids, title


# 使用示例
if __name__ == "__main__":
    # 对系列视频进行总结（使用全局配置的API_KEY）
    summarize_series_videos(
        mid="",
        series_name="",
        api_key=API_KEY,  # 使用全局配置
        max_pages=60,  # 限制页数避免处理太多
        output_file="summaries.json",  # 输出文件名
        verify_rounds=2,  # 验证轮数：第1轮总结，第2-3轮用不同弹幕验证修改
        enable_format=True,  # 最后进行格式规整
        enable_concurrent_request=False,  # 启用并发请求，提速处理，很容易风控，慎用
        max_workers=1  # 最大并发数，建议2-5之间，避免API限流
    )