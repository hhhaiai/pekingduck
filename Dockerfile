# 使用官方Python镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 以root用户安装系统依赖
RUN apt-get update && apt-get install -y \
    fonts-ipafont-gothic \
    fonts-wqy-zenhei \
    fonts-thai-tlwg \
    fonts-kacst \
    fonts-freefont-ttf \
    libxss1 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
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
RUN useradd -m -d /home/playwright playwright

# 设置环境变量
ENV PLAYWRIGHT_BROWSERS_PATH=/home/playwright/.cache/ms-playwright
ENV PATH="/home/playwright/.local/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV DEBUG=false
ENV PORT=7860

# 复制package.json和package-lock.json并安装Node.js依赖
COPY package*.json ./
RUN npm install

# 复制requirements.txt并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install firefox --with-deps

# 设置必要的目录和权限
RUN mkdir -p /home/playwright/.cache/ms-playwright && \
    chown -R playwright:playwright /home/playwright && \
    chmod -R 755 /home/playwright/.cache

# 复制项目文件并设置权限
COPY --chown=playwright:playwright . .

# 切换到非root用户
USER playwright

# 暴露端口
EXPOSE 7860

# 启动命令
CMD ["python", "more_core.py"]