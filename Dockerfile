FROM ghcr.io/astral-sh/uv:python3.12-bookworm

ENV TZ='Asia/Shanghai' PYTHONUNBUFFERED='1' PYTHONIOENCODING='utf-8'

# Microsoft YaHei,微软雅黑
COPY /usr/share/fonts/windows10-fonts/msyhbd.ttc /usr/share/fonts/window/msyhbd.ttc

# 安装依赖
RUN apt-get update -y &&  \
    apt-get install unzip wget -y && \
    wget https://mirrors.tuna.tsinghua.edu.cn/adobe-fonts/source-han-serif/SubsetOTF/SourceHanSerifCN.zip && \
    unzip SourceHanSerifCN.zip -d /usr/share/fonts && \
    fc-cache -f -v && \
    rm -rf SourceHanSerifCN.zip && \
    apt-get clean

RUN apt-get install -y libreoffice libmagic1 && \
    wget https://github.com/jgm/pandoc/releases/download/3.6.4/pandoc-3.6.4-1-amd64.deb && \
    dpkg -i pandoc-3.6.4-1-amd64.deb && \
    rm -rf pandoc-3.6.4-1-amd64.deb && \
    wget https://github.com/typst/typst/releases/download/v0.13.1/typst-x86_64-unknown-linux-musl.tar.xz && \
    tar -xvf typst-x86_64-unknown-linux-musl.tar.xz && \
    mv typst-x86_64-unknown-linux-musl/typst /usr/local/bin/typst && \
    rm -rf typst-x86_64-unknown-linux-musl.tar.xz && \
    apt-get clean




# uv，以及相关依赖

WORKDIR /app

COPY ./src/ .
RUN uv sync

ENTRYPOINT [ "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000" ]

