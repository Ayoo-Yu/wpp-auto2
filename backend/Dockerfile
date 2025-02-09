# 使用 Miniconda 基础镜像
FROM continuumio/miniconda3

# 设置工作目录
WORKDIR /app

# 复制 environment.yml
COPY environment.yml .

# 创建 Conda 环境
RUN conda env create -f environment.yml && conda clean --all --yes

# 激活环境
ENV PATH /opt/conda/envs/wind-power-env/bin:$PATH

# 复制项目代码
COPY . .

# 暴露端口
EXPOSE 5000

# 启动应用
CMD ["python", "app.py"]
