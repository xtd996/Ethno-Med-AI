FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu20.04

# 安装基本工具
RUN apt-get update && apt-get install -y \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 设置 Conda 安装路径
ENV CONDA_DIR=/opt/conda
RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \
    /bin/bash /tmp/miniconda.sh -b -p $CONDA_DIR && \
    rm /tmp/miniconda.sh && \
    $CONDA_DIR/bin/conda init bash && \
    echo "export PATH=$CONDA_DIR/bin:$PATH" >> ~/.bashrc

# 更新 PATH 环境变量
ENV PATH=$CONDA_DIR/bin:$PATH

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY web/backend/backend.py /app/
COPY RAG/ /app/RAG/
COPY environment.yml /app/

# 创建基础环境并安装 PyTorch GPU 版本
RUN conda env create -f environment.yml && \
    conda run -n py310 conda install pytorch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 pytorch-cuda=11.8 -c pytorch -c nvidia && \
    conda run -n py310 pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    conda clean --all --yes

# 设置默认 Shell 并激活环境
SHELL ["/bin/bash", "-c"]
RUN echo "source activate py310" >> ~/.bashrc

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["bash", "-c", "source activate py310 && uvicorn backend:app --host 0.0.0.0 --port 8000"]