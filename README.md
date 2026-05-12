# Tilt Detection Service

FastAPI 图片倾斜检测服务。部署目标：

- 项目目录：`/home/liuxiaoqing/tias_yxy_0923/detect_tilt`
- 对外地址：`http://10.80.5.197:8881/detect_tilt`
- Postman 请求方式：`POST`，`Body -> raw`，直接粘贴图片 base64 字符串

## 重要说明

构建阶段可以联网，服务运行时不会访问互联网。依赖会在 Docker build 时安装进镜像。

当前算法使用 `opencv-python-headless` 的 OpenCV 线段检测。该 pip 包默认不带 CUDA，所以算法计算本身不是 CUDA 加速。项目会强制容器挂载指定 GPU 并长期运行在 GPU 服务器上；如果后续必须让检测计算本身走 CUDA，需要换成 CUDA OpenCV 自编译镜像或改为 GPU 推理模型。

## GPU 前置检查

服务器需要安装 NVIDIA 驱动和 NVIDIA Container Toolkit。

宿主机检查：

```bash
nvidia-smi
```

容器 GPU 检查：

```bash
sudo docker run --rm --gpus all python:3.10-slim python -c "import os; print(os.getenv('NVIDIA_VISIBLE_DEVICES'))"
```

如果 Docker 不识别 `--gpus`，需要先安装 NVIDIA Container Toolkit。

## Docker 部署

进入项目目录：

```bash
cd /home/liuxiaoqing/tias_yxy_0923/detect_tilt
mkdir -p logs
```

默认使用第 1 块 GPU：

```bash
sudo env GPU_DEVICE=0 docker compose up -d --build
```

指定第 2 块 GPU：

```bash
sudo env GPU_DEVICE=1 docker compose up -d --build
```

指定第 3 块 GPU：

```bash
sudo env GPU_DEVICE=2 docker compose up -d --build
```

如果 PyPI 下载不稳定，推荐指定清华源：

```bash
sudo env PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple GPU_DEVICE=0 docker compose build --no-cache
sudo env GPU_DEVICE=0 docker compose up -d
```

如果出现类似 `PACKAGES DO NOT MATCH THE HASHES`，通常是网络、代理或缓存导致 wheel 下载损坏。处理方式：

```bash
sudo docker builder prune -f
sudo env PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple PIP_EXTRA_ARGS="--retries 20 --timeout 300" GPU_DEVICE=0 docker compose build --no-cache
sudo env GPU_DEVICE=0 docker compose up -d
```

查看服务：

```bash
sudo docker compose ps
sudo docker logs -f tilt-api
```

健康检查：

```bash
curl http://127.0.0.1:8881/health
```

返回里的 `gpu` 字段会显示容器内 GPU 挂载信息。

## Postman 测试

1. Method 选择 `POST`
2. URL 填 `http://10.80.5.197:8881/detect_tilt`
3. Body 选择 `raw`
4. raw 内容直接粘贴图片 base64 字符串
5. Header 可用 `Content-Type: text/plain`

成功返回示例：

```json
{
  "code": 200,
  "is_tilted": true,
  "angle": 2.85,
  "cost_ms": 18.17,
  "msg": "检测完成"
}
```

## 压测

先准备一张测试图片，例如 `test.jpg`，然后执行：

```bash
python3 scripts/benchmark.py --image ./test.jpg --url http://127.0.0.1:8881/detect_tilt --requests 1000 --concurrency 50
```

参数说明：

- `--requests 1000`：总请求数
- `--concurrency 50`：并发数
- `--url`：压测地址，服务器本机建议用 `127.0.0.1`

压测结果会输出成功数、失败数、QPS、平均耗时、P50、P90、P95、P99。

## 修改阈值

编辑 `config.toml`：

```toml
[detection]
tilt_threshold = 1.5
```

修改后重载配置：

```bash
curl -X POST http://127.0.0.1:8881/config/reload
```

## 运行时离线

服务启动后不会访问互联网。只要镜像构建成功，现场运行时断网也可以继续服务。

如果后续构建阶段也不能联网，请提前在有网机器下载依赖：

```bash
pip download -r requirements.txt -d wheels
```

然后现场离线构建：

```bash
sudo env PIP_INSTALL_MODE=offline GPU_DEVICE=0 docker compose up -d --build
```

当前 Dockerfile 使用 `python:3.10-slim`，不再拉取 1GB 以上的 CUDA 基础镜像。GPU 挂载由 NVIDIA Container Toolkit 和 `docker-compose.yml` 的 `device_ids` 完成。
