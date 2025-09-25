# 使用官方Python镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    # Node.js安装所需的依赖
    curl \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 安装Node.js 20.x和npm
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get update && \
    apt-get install -y nodejs && \
    npm install -g npm@latest && \
    rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN useradd -m -d /home/appuser appuser

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV DEBUG=false
ENV PORT=7860

# 复制package.json和package-lock.json并安装Node.js依赖
COPY package*.json ./
RUN npm install

# 复制requirements.txt并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件并设置权限
COPY --chown=appuser:appuser . .

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 7860

# 启动命令
CMD ["python", "more_core.py"]