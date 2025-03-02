# # 使用 Miniconda 基础镜像
# FROM continuumio/miniconda3

# # 设置工作目录
# WORKDIR /app

# # 复制 environment.yml
# COPY environment.yml .

# # 创建 Conda 环境
# RUN conda env create -f environment.yml && conda clean --all --yes

# # 激活环境
# ENV PATH /opt/conda/envs/wind-power-env/bin:$PATH

# # 复制项目代码
# COPY . .

# # 暴露端口
# EXPOSE 5000

# # 启动应用
# CMD ["python", "app.py"]

FROM continuumio/miniconda3

# 安装Node.js环境（PM2依赖）
RUN apt-get update && apt-get install -y curl && \
    curl -sL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g pm2 && \
    echo "PM2安装路径: $(which pm2)" && \
    # 不创建符号链接，直接使用npm全局安装的路径
    echo "export PM2_PATH=$(which pm2)" >> /etc/environment

# 设置工作目录
WORKDIR /app

# 复制环境配置
COPY environment.yml .
RUN conda env create -f environment.yml && conda clean --all --yes

# 激活Conda环境
ENV PATH /opt/conda/envs/wind-power-env/bin:$PATH

# 复制项目代码
COPY . .

# 创建PM2配置文件
RUN echo "module.exports = { apps: [{\
  name: 'python-app',\
  script: 'app.py',\
  interpreter: 'python',\
  autorestart: true,\
  watch: false,\
  env: { NODE_ENV: 'production' }\
}] }" > ecosystem.config.js

# 创建启动脚本
RUN echo '#!/bin/bash\n\
echo "检查PM2安装状态..."\n\
python check_pm2.py\n\
echo "启动应用..."\n\
pm2-runtime start ecosystem.config.js\n\
' > start.sh && chmod +x start.sh

# 暴露端口
EXPOSE 5000

# 使用启动脚本
CMD ["./start.sh"]