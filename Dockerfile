# ============================================================
# 三国杀终端版 — Docker 部署
# ============================================================
# 多阶段构建: builder(安装依赖) → runtime(精简运行)
# ============================================================

# ---------- Stage 1: Builder ----------
FROM python:3.12-slim AS builder

WORKDIR /build

# 仅复制依赖描述文件以利用缓存
COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

# ---------- Stage 2: Runtime ----------
FROM python:3.12-slim AS runtime

LABEL maintainer="Sanguosha Team"
LABEL description="三国杀终端版 — WebSocket 游戏服务器"

# 安全：非 root 用户运行
RUN groupadd -r sanguosha && useradd -r -g sanguosha -d /app sanguosha

WORKDIR /app

# 从 builder 拷贝已安装的依赖
COPY --from=builder /install /usr/local

# 复制项目代码
COPY . .

# 确保数据目录存在且有权限
RUN mkdir -p /app/logs /app/saves && \
    chown -R sanguosha:sanguosha /app

USER sanguosha

# WebSocket 服务端口
EXPOSE 8765

# 健康检查（每 30 秒检测 WebSocket 端口可达）
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(3); s.connect(('localhost',8765)); s.close()" || exit 1

# 默认启动 WebSocket 服务器
CMD ["python", "-m", "net.server", "--host", "0.0.0.0", "--port", "8765"]
