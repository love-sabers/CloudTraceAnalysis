# 2026年工业 Trace 操作手册

## 执行摘要

本手册只聚焦上一份报告中出现的 **2026 年 trace**，并按官方 `alibaba/clusterdata` 仓库逐项核验。根据仓库根目录与 README，截至 **2026-05-20**，公开可见、以 2026 命名的 trace 只有两个：`cluster-trace-v2026-GenAI` 和 `cluster-trace-v2026-spot-gpu`；我没有在同一官方仓库中看到第三个 2026 trace 目录。citeturn3view1turn4view2

这两个数据集的发布方式都比 Google BigQuery 或 Azure 打包集更“直接”：它们都在 **公共 GitHub 仓库** 中公开托管。`cluster-trace-v2026-GenAI` 既有 README 中描述的原始 CSV 结构，也在目录页列出了多个 `.tar.gz` 指标包与一个未文档化的 `data_trace_processed.tar.gz`；`cluster-trace-v2026-spot-gpu` 则是更简单的两个 CSV 表。citeturn5view0turn5view1turn4view0turn4view1

从“直接上手”角度看，**GenAI** 更适合先从 `lora_request_trace.csv` 和几个代表性指标包开始；**spot-gpu** 则建议先用 `job_info_df.csv` 做主分析，再用 `node_info_df.csv` 做容量背景表。由于官方没有给出某些硬件细节，例如精确机架拓扑、网络带宽、存储介质类型，所以这些项在本文中均明确标注为“官方未说明”。citeturn4view0turn4view1

## 2026年 Trace 范围总览

官方 `alibaba/clusterdata` 根目录当前展示的子目录中，只有 `cluster-trace-v2026-GenAI` 和 `cluster-trace-v2026-spot-gpu` 两个 2026 目录；根 README 也只显式介绍了其中的 `cluster-trace-v2026-GenAI`，而 `cluster-trace-v2026-spot-gpu` 通过目录页和其子 README 独立发布。仓库整体是 **Public**，适合直接按 GitHub/Raw URL 下载，不需要 BigQuery、Google Storage、问卷申请或登录审批。citeturn3view1turn4view2turn2view0turn2view1

| Trace | 官方场景描述 | 访问方式 | 数据格式与压缩 | 官方给出的集群配置 | 官方未说明项 |
| --- | --- | --- | --- | --- | --- |
| `cluster-trace-v2026-GenAI` | 大规模 Stable Diffusion / GenAI serving 的 top-down trace，覆盖应用层、中间件层、基础设施层 | 公共 GitHub 仓库；可通过 GitHub 页面与 Raw HTTP(s) 访问 | README 中给出 CSV 结构；目录中列出多个 `.tar.gz`、一个 `.csv`、一个 `.ipynb`、一个 `.png` | 有 Kubernetes Pod 级 GPU/内存指标，支持通过 `container_ip` 做跨文件关联；系统属于生产 serverless inference 环境 | 机器数量、GPU 型号与数量、网络、拓扑、存储类型/带宽 |
| `cluster-trace-v2026-spot-gpu` | 采用 spot GPU 资源的 AI 作业 trace，区分 HP 与 Spot 作业 | 公共 GitHub 仓库；可通过 GitHub 页面与 Raw HTTP(s) 访问 | 两个纯 CSV：`node_info_df.csv`、`job_info_df.csv` | **4278 个 GPU 节点**、**6 种 GPU 卡类型**；节点表给出 `gpu_model`、`gpu_capacity_num`、`cpu_num` | 网络、存储、节点拓扑、作业状态、作业到节点的放置映射 |

上表依据官方仓库根目录、两个 2026 子目录页和两个 README 整理。citeturn3view1turn4view2turn5view0turn5view1turn4view0turn4view1

## cluster-trace-v2026-GenAI

### 元数据与官方说明

`cluster-trace-v2026-GenAI` 的官方名称是 **GenAI Serving Top-Down Dataset 2026 (GenTD26)**。README 说明它提供了一个大规模生成式 AI 服务系统的 **top-down** 视图，覆盖三层：**应用层**（user requests 和 end-to-end latency）、**中间件层**（gateway queues、schedulers、pipeline management）与 **基础设施层**（container resources、GPU utilization、memory usage）。根 README 还明确把它描述为一个 **large-scale stable diffusion model serving system**；子 README 补充说明这是一类真实生产的 **serverless inference systems**，并已做时间偏移、指标缩放和标识符哈希匿名化。citeturn4view2turn5view0turn4view0

| 项目 | 官方信息 |
| --- | --- |
| 数据集名称 | GenAI Serving Top-Down Dataset 2026 (`GenTD26`) |
| 官方目录 | `cluster-trace-v2026-GenAI` |
| 发布形态 | 公共 GitHub 子目录 |
| 访问方式 | GitHub 页面浏览；Raw HTTP(s) 可直接取 README/CSV/压缩包 |
| 应用场景 | Stable Diffusion / GenAI serving，生产 serverless inference |
| 架构层次 | 应用层、中间件层、基础设施层 |
| 关联键 | `container_ip`，README 说明可跨文件关联系统与服务性能 |
| 匿名化方式 | timestamp shifting、metric scaling、identifier hashing；字段如 `container_ip`、model id 使用 MD5 哈希 |
| 集群配置 | 官方仅明示存在 Kubernetes pod 级指标与 GPU/内存指标；机器/GPU 总数未说明 |
| 网络/存储/拓扑 | 官方未说明；仅从字段定义可知存在“LoRA 从存储加载到 GPU memory”的路径 |
| 研究用途 | 性能分析、调度算法、容量规划、AIOps、异常检测 |

上表依据 GenAI 目录页与 README。citeturn5view0turn4view0

### 文件、字段与含义

README 给出的目录结构是 **CSV 视角**，但 GitHub 目录页同时列出了多个 `.tar.gz` 压缩文件。因此，实践中最好把它理解成“**README 描述的是逻辑 CSV 表；仓库实际提供的是若干 tar.gz + 少量直接 CSV**”。其中最值得注意的一个细节是：README 文本写的是 `base_model_update_latency_anon.csv`，但目录页里实际文件名写成了 `basemodel_update_latency_anon.tar.gz`；下载脚本应以仓库实际文件名为准。citeturn5view0turn4view0

| 逻辑文件 | 仓库中可见发布形态 | 关键字段 | 字段含义与单位 |
| --- | --- | --- | --- |
| `qps.csv` | `qps.tar.gz` | `timestamp_anon`, `value`, `container_ip`, `request_type` | 匿名时间戳（秒）、QPS 值、容器 IP 哈希、请求类型 |
| `queue_size_raw_anon.csv` | `queue_size_raw_anon.tar.gz` | `timestamp_anon`, `value`, `container_ip` | 匿名时间戳、队列长度（任务数）、容器 IP 哈希 |
| `queue_rt_raw_anon.csv` | `queue_rt_raw_anon.tar.gz` | `timestamp_anon`, `value`, `container_ip` | 匿名时间戳、排队时间（毫秒）、容器 IP 哈希 |
| `pipeline_update_latency_anon.csv` | `pipeline_update_latency_anon.tar.gz` | `timestamp_anon`, `value`, `container_ip` | 完整 pipeline 更新/切换时延（毫秒） |
| `base_model_update_latency_anon.csv` | `basemodel_update_latency_anon.tar.gz` | `timestamp_anon`, `value`, `container_ip` | base model 加载时延（毫秒） |
| `lora_update_latency_anon.csv` | `lora_update_latency_anon.tar.gz` | `timestamp_anon`, `value`, `container_ip` | LoRA adapter 加载时延（毫秒） |
| `controlnet_latency_data_anon.csv` | `controlnet_latency_data_anon.tar.gz` | `timestamp_anon`, `value`, `container_ip` | ControlNet 加载时延（毫秒） |
| `pod_memory_util_anon.csv` | `pod_memory_util_anon.tar.gz` | `timestamp_anon`, `value`, `container_ip` | Pod 内存利用率（百分比） |
| `pod_gpu_duty_cycle_anon.csv` | `pod_gpu_duty_cycle_anon.tar.gz` | `timestamp_anon`, `value`, `container_ip` | Pod GPU 利用率（百分比） |
| `pod_gpu_memory_used_bytes_anon.csv` | `pod_gpu_memory_used_bytes_anon.tar.gz` | `timestamp_anon`, `value`, `container_ip` | Pod GPU 显存占用（字节） |
| `model_predict_data_anon.csv` | `model_predict_data_anon.tar.gz` | `timestamp_anon`, `value`, `container_ip` | 纯推理时延（毫秒） |
| `pipeline_inference_data_anon.csv` | `pipeline_inference_data_anon.tar.gz` | `timestamp_anon`, `value`, `container_ip` | 端到端推理 RT（毫秒） |
| `lora_request_trace.csv` | **直接 CSV** 与 `lora_request_trace.tar.gz` 同时存在 | `gmt_create`, `predict_type`, `predict_status`, `exec_time_seconds`, `groupId`, `prompt_length`, `negative_prompt_length`, `num_images_per_prompt`, `num_inference_steps`, `checkpoint_model_version_id`, `num_lora` | 请求创建时间、任务类型、状态、执行时长（秒）、匿名 group/user、prompt 复杂度、推理步数、模型版本、LoRA 数 |
| 其他 | `data_trace_processed.tar.gz`, `lora_request_processing.ipynb`, `MLoRA-Pipeline.png` | — | `data_trace_processed.tar.gz` 在目录页可见，但 README 未解释其内容；`ipynb` 为官方 notebook |

这张表基于官方 README 的逻辑字段描述和 GitHub 目录页的实际文件名整理。citeturn5view0turn4view0

### 下载与访问说明

从发布方式看，GenAI 数据集是 **直接 HTTP(s) 可达** 的公共 GitHub 文件。最稳妥的做法，是优先下载你要用的少数原始表，而不是整仓 clone。若你只做请求分析，首选 `lora_request_trace.csv`；若你还要做跨层时间对齐，再补 `qps.tar.gz`、`queue_rt_raw_anon.tar.gz`、`pipeline_inference_data_anon.tar.gz`、`pod_gpu_duty_cycle_anon.tar.gz` 等代表性指标包。citeturn5view0turn4view0

```bash
# 推荐：只下载首选样本与几个常用指标包
BASE="https://raw.githubusercontent.com/alibaba/clusterdata/master/cluster-trace-v2026-GenAI"
mkdir -p data/genai && cd data/genai

wget -c "${BASE}/README.md"
wget -c "${BASE}/lora_request_trace.csv"
wget -c "${BASE}/qps.tar.gz"
wget -c "${BASE}/queue_rt_raw_anon.tar.gz"
wget -c "${BASE}/pipeline_inference_data_anon.tar.gz"
wget -c "${BASE}/pod_gpu_duty_cycle_anon.tar.gz"

# 若你更倾向 curl
curl -L -O "${BASE}/lora_request_trace.csv"
curl -L -O "${BASE}/qps.tar.gz"
```

```bash
# 若要尽量完整地下载官方目录中的主要归档文件
BASE="https://raw.githubusercontent.com/alibaba/clusterdata/master/cluster-trace-v2026-GenAI"
files=(
  "basemodel_update_latency_anon.tar.gz"
  "controlnet_latency_data_anon.tar.gz"
  "data_trace_processed.tar.gz"
  "lora_request_trace.tar.gz"
  "lora_update_latency_anon.tar.gz"
  "model_predict_data_anon.tar.gz"
  "pipeline_inference_data_anon.tar.gz"
  "pipeline_update_latency_anon.tar.gz"
  "pod_gpu_duty_cycle_anon.tar.gz"
  "pod_gpu_memory_used_bytes_anon.tar.gz"
  "pod_memory_util_anon.tar.gz"
  "qps.tar.gz"
  "queue_rt_raw_anon.tar.gz"
  "queue_size_raw_anon.tar.gz"
)

mkdir -p data/genai_full && cd data/genai_full
for f in "${files[@]}"; do
  wget -c "${BASE}/${f}"
done
```

### 解压与预处理建议

如果你只处理 `lora_request_trace.csv`，这类任务用 **8–16GB RAM**、**10–20GB 可用磁盘** 就足够；如果你打算同时处理多个 tar.gz 指标包并做跨层对齐，建议把环境提高到 **16–32GB RAM**、**50GB 以上磁盘**、**4–8 个 CPU 线程**。这是操作建议，不是官方硬件要求。更重要的是：GenAI README 明确指出原始采样粒度很细，推荐按 **10 分钟** 等时间窗聚合；同时建议统一把 `"NULL"` 和 `None` 视为缺失值。citeturn4view0

在解压方式上，若文件较大，不建议一次性全部展开到同一目录；更稳妥的是“**一包一目录**”或“**流式读取**”。若机器 CPU 富余，可优先用 `pigz` 加速解压；若打算重复分析，建议第一次把 CSV 清洗后转成 Parquet，再做后续聚合。

```bash
# 单文件单目录解压，便于管理
mkdir -p extracted/qps
tar -xzf qps.tar.gz -C extracted/qps

# 多个 tar.gz 并行解压；-P4 表示并行 4 个任务，可按机器核数调整
find . -maxdepth 1 -name "*.tar.gz" -print0 | \
  xargs -0 -n1 -P4 -I{} sh -c '
    d="extracted/$(basename "{}" .tar.gz)"
    mkdir -p "$d"
    tar -xzf "{}" -C "$d"
  '
```

### Python 读取与初步清洗示例

下面的示例满足几个目标：  
一是可以**直接复制运行**；  
二是同时演示 **未压缩 CSV** 与 **tar.gz 中 CSV 的流式读取**；  
三是展示如何构造 **请求生命周期**、如何处理 **缺失值 / 在途请求删失**、以及如何按 **任务类型 / group / 时间窗口** 聚合。  
示例默认 Linux + Python 3.10+。GenAI 的时间字段有两类：`gmt_create` 是带偏移的 datetime；`timestamp_anon` 是匿名秒级时间戳，更适合做跨文件相对对齐。citeturn4view0

```bash
python3 -m pip install -U pandas pyarrow fsspec requests
```

```python
#!/usr/bin/env python3
"""
读取 Alibaba cluster-trace-v2026-GenAI 的首选样本与一个指标包：
1) 读取 lora_request_trace.csv（支持 HTTP(s) 或本地文件）
2) 读取 qps.tar.gz（流式读取 tar.gz 中的 CSV）
3) 解析时间戳、构造 finish_time / is_censored
4) 按 predict_type / groupId / 日窗口 和 request_type / 10分钟窗口做聚合
"""

from __future__ import annotations

import sys
import tarfile
from pathlib import Path

import fsspec
import pandas as pd


GENAI_REQ = "https://raw.githubusercontent.com/alibaba/clusterdata/master/cluster-trace-v2026-GenAI/lora_request_trace.csv"
GENAI_QPS_TAR = "https://raw.githubusercontent.com/alibaba/clusterdata/master/cluster-trace-v2026-GenAI/qps.tar.gz"

REQ_DTYPES = {
    "predict_type": "string",
    "predict_status": "string",
    "groupId": "string",
    "checkpoint_model_version_id": "string",
    "prompt_length": "float64",
    "negative_prompt_length": "float64",
    "num_images_per_prompt": "float64",
    "num_inference_steps": "float64",
    "num_lora": "Int64",
    "exec_time_seconds": "float64",
}

METRIC_DTYPES = {
    "timestamp_anon": "float64",
    "value": "float64",
    "container_ip": "string",
    "request_type": "string",
}

NA_VALUES = ["NULL", "None", "nan", ""]


def iter_csv_chunks(path_or_url: str, chunksize: int = 200_000):
    """分块读取普通 CSV。"""
    try:
        with fsspec.open(path_or_url, mode="rt", compression=None) as f:
            yield from pd.read_csv(
                f,
                chunksize=chunksize,
                dtype=REQ_DTYPES,
                na_values=NA_VALUES,
            )
    except Exception as e:
        raise RuntimeError(f"读取 CSV 失败: {path_or_url}") from e


def iter_first_csv_from_tar_gz(path_or_url: str, chunksize: int = 300_000):
    """流式读取 tar.gz 中的第一个 CSV；适合 GitHub raw URL 或本地 tar.gz。"""
    try:
        with fsspec.open(path_or_url, mode="rb") as fh:
            # r|gz 是顺序流式模式，不会先把整个归档读入内存
            with tarfile.open(fileobj=fh, mode="r|gz") as tar:
                for member in tar:
                    if member.isfile() and member.name.endswith(".csv"):
                        extracted = tar.extractfile(member)
                        if extracted is None:
                            continue
                        yield from pd.read_csv(
                            extracted,
                            chunksize=chunksize,
                            dtype=METRIC_DTYPES,
                            na_values=NA_VALUES,
                        )
                        return
        raise FileNotFoundError(f"在归档中未找到 CSV: {path_or_url}")
    except Exception as e:
        raise RuntimeError(f"读取 tar.gz 失败: {path_or_url}") from e


def clean_request_chunk(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # README 说明 gmt_create 是偏移后的 datetime；相对顺序可用，绝对日期不应外推到真实日历事件
    df["gmt_create"] = pd.to_datetime(df["gmt_create"], errors="coerce")
    df["exec_time_seconds"] = pd.to_numeric(df["exec_time_seconds"], errors="coerce")
    df["negative_prompt_length"] = pd.to_numeric(df["negative_prompt_length"], errors="coerce")

    # 这里把终态限定为 SUCCEED / FAILED；其他状态视作仍在进行或右删失
    terminal = df["predict_status"].isin(["SUCCEED", "FAILED"])
    valid_duration = df["exec_time_seconds"].notna() & (df["exec_time_seconds"] >= 0)
    valid_start = df["gmt_create"].notna()

    df["is_censored"] = ~(terminal & valid_duration & valid_start)
    df["finish_time"] = pd.NaT

    mask = ~df["is_censored"]
    df.loc[mask, "finish_time"] = (
        df.loc[mask, "gmt_create"]
        + pd.to_timedelta(df.loc[mask, "exec_time_seconds"], unit="s")
    )

    df["day_bucket"] = df["gmt_create"].dt.floor("D")
    return df


def clean_qps_chunk(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["timestamp_anon"] = pd.to_numeric(df["timestamp_anon"], errors="coerce")
    # 匿名时间戳用“相对秒”处理，不强行赋予真实绝对时间语义
    df = df.dropna(subset=["timestamp_anon", "value"])
    bucket_s = (df["timestamp_anon"] // 600) * 600  # 10 分钟窗
    df["bucket_10m"] = pd.to_timedelta(bucket_s, unit="s")
    return df


def main():
    req_parts = []
    qps_parts = []

    # 请求表：按块清洗，再聚合
    for chunk in iter_csv_chunks(GENAI_REQ, chunksize=200_000):
        c = clean_request_chunk(chunk)
        agg = (
            c.groupby(["predict_type", "groupId", "day_bucket"], dropna=False)
            .agg(
                requests=("predict_status", "size"),
                succeed=("predict_status", lambda s: (s == "SUCCEED").sum()),
                failed=("predict_status", lambda s: (s == "FAILED").sum()),
                censored=("is_censored", "sum"),
                mean_exec_s=("exec_time_seconds", "mean"),
                p95_exec_s=("exec_time_seconds", lambda x: x.quantile(0.95)),
                mean_prompt_len=("prompt_length", "mean"),
                mean_steps=("num_inference_steps", "mean"),
            )
            .reset_index()
        )
        req_parts.append(agg)

    # 指标包：演示如何用 tar.gz 流式读取 QPS
    for chunk in iter_first_csv_from_tar_gz(GENAI_QPS_TAR, chunksize=300_000):
        c = clean_qps_chunk(chunk)
        agg = (
            c.groupby(["request_type", "bucket_10m"], dropna=False)
            .agg(
                points=("value", "size"),
                qps_sum=("value", "sum"),
                qps_mean=("value", "mean"),
            )
            .reset_index()
        )
        qps_parts.append(agg)

    req_summary = (
        pd.concat(req_parts, ignore_index=True)
        .groupby(["predict_type", "groupId", "day_bucket"], dropna=False)
        .sum(numeric_only=True)
        .reset_index()
        .sort_values(["day_bucket", "predict_type", "groupId"])
    )

    qps_summary = (
        pd.concat(qps_parts, ignore_index=True)
        .groupby(["request_type", "bucket_10m"], dropna=False)
        .sum(numeric_only=True)
        .reset_index()
        .sort_values(["bucket_10m", "request_type"])
    )

    out_dir = Path("out_genai")
    out_dir.mkdir(exist_ok=True)
    req_summary.to_parquet(out_dir / "genai_request_daily.parquet", index=False)
    qps_summary.to_parquet(out_dir / "genai_qps_10min.parquet", index=False)

    print("== 请求日聚合样例 ==")
    print(req_summary.head(10).to_string(index=False))
    print("\n== QPS 10分钟聚合样例 ==")
    print(qps_summary.head(10).to_string(index=False))
    print(f"\n输出目录: {out_dir.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("用户中断。", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"运行失败: {e}", file=sys.stderr)
        sys.exit(1)
```

### 注意事项与常见问题

GenAI 数据集最容易踩的坑有三个。第一，`gmt_create` 虽然长得像正常 datetime，但 README 明确说明时间戳做了 **time offset** 匿名化，因此可用于顺序、窗口和生命周期分析，但不应直接映射到真实业务节假日或外部事件日历。第二，README 一方面说“所有文件可通过 `container_ip` 关联”，另一方面它给出的 `lora_request_trace.csv` 字段表又没有显式列出 `container_ip`；因此跨层 join 前，最好先 `head -n 2` 检查实际 header，不要在代码里先验假设请求表一定含 `container_ip`。第三，目录中有 `data_trace_processed.tar.gz`，但 README 并未解释其 schema；做正式研究时不应把它当成首选证据，应优先使用 README 明确说明过的原始逻辑表。citeturn4view0turn5view0

官方链接：官方目录页与文件清单。citeturn2view0turn5view0 官方 README 与字段说明。citeturn4view0 根 README 中对该数据集的总览。citeturn4view2 README 列出的相关论文包括 SoCC’25 的数据集论文题名、CLUSTER’25 的 Rock，以及 EuroSys’26 的 FlexPipe。citeturn4view0turn8academia1

## cluster-trace-v2026-spot-gpu

### 元数据与官方说明

`cluster-trace-v2026-spot-gpu` 的官方 README 将其描述为 **Traces for AI jobs leveraging spot GPU resources**。它区分两类作业：**High-Priority (HP)** 与 **Spot**；其中 HP 具有严格 SLO，Spot 使用 opportunistic spot instances。官方还明确给出了集群概貌：节点数据集覆盖 **4278 个 GPU 节点**，共有 **6 种 GPU 卡类型**。与 GenAI 相比，这个数据集更“窄而深”：只有一张**节点表**和一张**作业表**，但足以做资源供给、作业到达、时长分布和 HP/Spot 差异分析。citeturn5view1turn4view1

| 项目 | 官方信息 |
| --- | --- |
| 数据集名称 | Traces for AI jobs leveraging spot GPU resources |
| 官方目录 | `cluster-trace-v2026-spot-gpu` |
| 发布形态 | 公共 GitHub 子目录 |
| 访问方式 | GitHub 页面浏览；Raw HTTP(s) 下载两个 CSV |
| 主要表 | `node_info_df.csv`、`job_info_df.csv` |
| 官方给出的集群规模 | **4278 GPU nodes** |
| GPU 型号类别数 | **6 GPU card types** |
| 已知字段维度 | 节点级 GPU 型号、GPU 数量、CPU 核数；作业级组织、资源请求、worker 数、相对提交时间、时长、作业类型 |
| 网络/存储/机架/拓扑 | 官方未说明 |
| 作业状态字段 | 官方未提供 |
| 节点-作业放置映射 | 官方未提供 |

上表依据 spot-gpu 目录页与 README。citeturn5view1turn4view1

### 文件、字段与含义

spot-gpu 的结构简单得多：目录页只列出 `README.md`、`job_info_df.csv` 与 `node_info_df.csv` 三个文件，没有 tar.gz 压缩包。官方 README 的字段说明已覆盖了这两个 CSV 的核心 schema；不过 README 文本中有一个小笔误——它先说 node dataset 在 `node_info_df.csv`，紧接着又写 “The node dataset is provided in the file `job_info_df.csv`”，但从字段表可知该文件实际是 **job/workload dataset**。citeturn5view1turn4view1

| 文件 | 关键字段 | 字段含义 |
| --- | --- | --- |
| `node_info_df.csv` | `node_name`, `gpu_model`, `gpu_capacity_num`, `cpu_num` | 节点 ID、GPU 型号、节点 GPU 容量数、CPU 核数（vCPU） |
| `job_info_df.csv` | `job_name`, `organization`, `gpu_model`, `cpu_request`, `gpu_request`, `worker_num`, `submit_time`, `duration`, `job_type` | 作业 ID、成本组织/租户、请求 GPU 型号、CPU 请求、GPU 请求、worker 数、相对提交时间、作业时长（秒）、HP/Spot 类型 |

这张表依据官方 README 与目录页整理。citeturn5view1turn4view1

### 下载与访问说明

spot-gpu 是标准的 **纯 CSV 直读型** 数据集。因为只有两个表，所以下载最简单：直接取两个 Raw CSV 即可。相比 Git clone，`wget -c` 或 `curl -L -O` 更适合大文件断点续传与脚本化。官方 README 中没有提申请、密码、BigQuery、Google Storage 或问卷入口。citeturn5view1turn4view1turn3view1

```bash
BASE="https://raw.githubusercontent.com/alibaba/clusterdata/master/cluster-trace-v2026-spot-gpu"
mkdir -p data/spot_gpu && cd data/spot_gpu

wget -c "${BASE}/README.md"
wget -c "${BASE}/node_info_df.csv"
wget -c "${BASE}/job_info_df.csv"

# 或者使用 curl
curl -L -O "${BASE}/node_info_df.csv"
curl -L -O "${BASE}/job_info_df.csv"
```

### 解压与预处理建议

因为它是两个直接 CSV，所以 spot-gpu 不需要解压。经验上，**4–8GB RAM**、**4–10GB 磁盘**、**2–4 个 CPU 线程** 就足够起步；如果 `job_info_df.csv` 很大，建议 `chunksize` 配到 **50 万到 100 万行**。节点表通常可以一次性读入内存，作业表建议分块读、边读边聚合。若后续会重复分析，建议立刻将分块结果落盘为 Parquet。  

对时间处理，最重要的一点是：`submit_time` 不是绝对 wall clock，而是“**与第一个提交作业相差多少秒**”。因此最安全的做法是把它转成 **相对 timedelta** 或者人为锚定到某个虚拟起点，例如 `1970-01-01`，只用于作图和窗口分桶，不赋予真实日期语义。这个定义来自官方字段说明。citeturn5view1turn4view1

### Python 读取与初步清洗示例

下面的示例完成四件事：  
一是读取节点表，汇总各 GPU 型号的节点数和总 GPU 容量；  
二是流式读取作业表；  
三是构造作业生命周期 `submit -> finish`；  
四是按 `job_type / gpu_model / organization / 日窗口` 聚合。  
由于官方没有给作业状态字段，这段代码不会尝试推断 success/failure/preemption，而只构造**观测到的作业时长生命周期**。citeturn5view1turn4view1

```bash
python3 -m pip install -U pandas pyarrow fsspec
```

```python
#!/usr/bin/env python3
"""
读取 Alibaba cluster-trace-v2026-spot-gpu：
1) 一次性读取 node_info_df.csv
2) 对 job_info_df.csv 进行分块读取
3) 解析 submit_time / duration，构造 submit_td / finish_td
4) 按 job_type、gpu_model、organization、day_bucket 聚合
"""

from __future__ import annotations

import sys
from pathlib import Path

import fsspec
import pandas as pd


NODE_URL = "https://raw.githubusercontent.com/alibaba/clusterdata/master/cluster-trace-v2026-spot-gpu/node_info_df.csv"
JOB_URL = "https://raw.githubusercontent.com/alibaba/clusterdata/master/cluster-trace-v2026-spot-gpu/job_info_df.csv"

NODE_DTYPES = {
    "node_name": "string",
    "gpu_model": "string",
    "gpu_capacity_num": "Int64",
    "cpu_num": "Int64",
}

JOB_DTYPES = {
    "job_name": "string",
    "organization": "string",
    "gpu_model": "string",
    "cpu_request": "float64",
    "gpu_request": "float64",
    "worker_num": "float64",
    "submit_time": "float64",
    "duration": "float64",
    "job_type": "string",
}


def read_nodes(path_or_url: str) -> pd.DataFrame:
    try:
        with fsspec.open(path_or_url, mode="rt") as f:
            return pd.read_csv(f, dtype=NODE_DTYPES)
    except Exception as e:
        raise RuntimeError(f"读取节点表失败: {path_or_url}") from e


def iter_jobs(path_or_url: str, chunksize: int = 1_000_000):
    try:
        with fsspec.open(path_or_url, mode="rt") as f:
            yield from pd.read_csv(f, dtype=JOB_DTYPES, chunksize=chunksize)
    except Exception as e:
        raise RuntimeError(f"读取作业表失败: {path_or_url}") from e


def clean_jobs(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    numeric_cols = ["cpu_request", "gpu_request", "worker_num", "submit_time", "duration"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 仅保留生命周期可构造的记录
    valid = (
        df["submit_time"].notna()
        & df["duration"].notna()
        & (df["duration"] >= 0)
    )
    df = df.loc[valid].copy()

    # submit_time 是“距第一个提交作业的秒数”，不是绝对时间戳
    df["submit_td"] = pd.to_timedelta(df["submit_time"], unit="s")
    df["finish_td"] = df["submit_td"] + pd.to_timedelta(df["duration"], unit="s")

    # 用相对日桶做时间窗口聚合
    df["day_bucket"] = (df["submit_time"] // 86400).astype("Int64")

    # 派生指标
    df["total_gpu_requested"] = df["gpu_request"] * df["worker_num"]
    df["total_cpu_requested"] = df["cpu_request"] * df["worker_num"]

    return df


def main():
    # 节点背景表：各 GPU 型号的节点数 / GPU 总量 / CPU 总量
    nodes = read_nodes(NODE_URL)
    node_summary = (
        nodes.groupby("gpu_model", dropna=False)
        .agg(
            node_count=("node_name", "nunique"),
            total_gpu_capacity=("gpu_capacity_num", "sum"),
            total_cpu_vcpu=("cpu_num", "sum"),
        )
        .reset_index()
        .sort_values("node_count", ascending=False)
    )

    # 作业表：流式聚合
    parts = []
    for chunk in iter_jobs(JOB_URL, chunksize=1_000_000):
        c = clean_jobs(chunk)
        agg = (
            c.groupby(["job_type", "gpu_model", "organization", "day_bucket"], dropna=False)
            .agg(
                jobs=("job_name", "count"),
                mean_duration_s=("duration", "mean"),
                p95_duration_s=("duration", lambda x: x.quantile(0.95)),
                total_gpu_requested=("total_gpu_requested", "sum"),
                total_cpu_requested=("total_cpu_requested", "sum"),
                avg_workers=("worker_num", "mean"),
            )
            .reset_index()
        )
        parts.append(agg)

    job_summary = (
        pd.concat(parts, ignore_index=True)
        .groupby(["job_type", "gpu_model", "organization", "day_bucket"], dropna=False)
        .sum(numeric_only=True)
        .reset_index()
        .sort_values(["day_bucket", "job_type", "gpu_model", "organization"])
    )

    out_dir = Path("out_spot_gpu")
    out_dir.mkdir(exist_ok=True)

    node_summary.to_parquet(out_dir / "spot_gpu_node_summary.parquet", index=False)
    job_summary.to_parquet(out_dir / "spot_gpu_job_daily.parquet", index=False)

    print("== 节点背景汇总 ==")
    print(node_summary.head(10).to_string(index=False))
    print("\n== 作业日聚合样例 ==")
    print(job_summary.head(10).to_string(index=False))
    print(f"\n输出目录: {out_dir.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("用户中断。", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"运行失败: {e}", file=sys.stderr)
        sys.exit(1)
```

### 注意事项与常见问题

spot-gpu 的几个关键限制都来自它“只发布了两个表”这一事实。第一，`submit_time` 是相对秒，不是绝对日期；因此时间窗口分析应使用相对日桶、相对小时桶，而不是外部日历。第二，官方字段里没有 `status`、`finish_reason`、`evicted`、`preempted` 这类列，因此不能仅凭发布表区分“正常完成”和“被抢占/被驱逐”。第三，节点表与作业表之间没有共享的 `node_name` 放置映射，所以你只能用 `gpu_model`、资源请求量和组织维度做容量背景分析，不能重建精确的 per-node placement。以上限制不是缺点，而是 released schema 的边界。citeturn5view1turn4view1

官方链接：官方目录页与文件清单。citeturn2view1turn5view1 官方 README 与字段说明。citeturn4view1 该目录 README 中内嵌了 ASPLOS’26 BibTeX，但论文超链接当前仍是占位符 `www.xxx`；若需要论文正文，可参考作者公开的 arXiv 预印本。citeturn5view1turn8academia0

## 通用下载与预处理流程

这两个 2026 trace 的最佳实践并不复杂：先从 **README 明确文档化的原始样本** 起步，再根据研究问题增量下载其余文件；不要一开始就追求“全量归档+无差别解压”。这一策略尤其适合 GenAI，因为其目录中既有原始请求 CSV，也有大量 tar.gz 指标包，还有一个 README 未详细解释的 processed 归档。citeturn5view0turn4view0

```mermaid
flowchart LR
A[核验官方 README 和目录页] --> B[按研究目标选择首选样本]
B --> C[用 wget -c 或 curl -L 下载]
C --> D{是否为 tar.gz}
D -- 是 --> E[tar 流式读取或按包解压]
D -- 否 --> F[pandas 或 pyarrow 直接分块读取]
E --> G[统一 NULL/None 缺失值]
F --> G
G --> H[解析时间戳与相对时间]
H --> I[构造生命周期 arrival/create -> finish/delete]
I --> J[标记删失样本与非法值]
J --> K[按任务类型 服务近似维度 时间窗口聚合]
K --> L[落盘 Parquet 供后续分析]
```

如果你在 Linux 上要做长期研究，比较实用的组合是：  
`wget -c` 或 `curl -L` 负责下载；  
`tar` / `pigz` 负责解压；  
`pandas.read_csv(chunksize=...)` 负责边读边聚合；  
`pyarrow` 负责落盘 Parquet；  
`dask.dataframe` 只在单机 pandas 已经明显吃紧时再上。  

一个很实用的小技巧是：**先按块聚合，再拼接聚合结果，而不是先拼完整表**。GenAI 的请求表和 spot-gpu 的作业表都适合这样处理。对 reproducibility 而言，建议后续把 `master` 分支的 raw URL 固定到某个 commit SHA，而不是长期依赖浮动分支名。

## 总体硬件与软件配置建议

下面这张表是“可直接动手”的经验建议，不是官方限制。它的目标是让你在第一次跑通脚本时尽量少踩坑。

| 场景 | 建议磁盘 | 建议内存 | 并行度 | 建议 chunk size | 推荐工具 |
| --- | --- | --- | --- | --- | --- |
| 仅处理 GenAI `lora_request_trace.csv` | 10–20GB | 8–16GB | 2–4 线程 | 20万–50万行 | pandas, pyarrow |
| 处理 GenAI 多个指标包并做跨层对齐 | 50GB+ | 16–32GB | 4–8 线程 | 20万–30万行 | pandas, pyarrow, tar, pigz |
| 仅处理 spot-gpu 两个 CSV | 4–10GB | 4–8GB | 2–4 线程 | 50万–100万行 | pandas, pyarrow |
| 长期反复分析与多人协作 | 100GB+ | 32GB+ | 8 线程左右 | 先分块再转 parquet | pandas, pyarrow, dask 可选 |

推荐的软件栈可以保守一些：**Python 3.10 或 3.11**，**pandas 2.x**，**pyarrow 14+**，**fsspec 新版本**，**requests 2.x**，再加上系统工具 `tar`、`pigz`、`zstd`、`parquet-tools`。若你只想把两个官方样本跑通，`pandas + pyarrow + fsspec` 已经足够；若准备长期维护分析管线，再补 `dask[dataframe]` 也不晚。  

最后再强调一遍与数据集本身强相关的两个实践点。其一，**GenAI 时间戳是匿名偏移时间**，**spot-gpu 时间戳是相对秒**，两者都不应直接解释为真实 wall clock。其二，若官方没有给出网络、拓扑、状态、节点放置等字段，就应当明确写“官方未说明”，不要把经验猜测写成数据集事实。前者来自两个 README 的时间字段定义，后者来自这两个已发布 schema 的边界。citeturn4view0turn4view1turn5view1