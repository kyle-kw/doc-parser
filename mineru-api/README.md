# MinerU 接口镜像构建

将MinerU解析PDF封装成API服务。可以离线使用。

## 构建镜像

```shell
docker compose build
```

构建中需要安装依赖和下载模型，比较慢。

## 启动服务

```shell
docker compose up -d
```

API文档：`http://localhost:8000/docs`

## 升级MinerU

可以使用下面镜像构建
```dockerfile
# 之前构建好的镜像tag
FROM mineru:latest

# 升级到最新版MinerU
RUN /bin/bash -c "source /opt/mineru_venv/bin/activate && pip install -U magic-pdf[full]"
```

