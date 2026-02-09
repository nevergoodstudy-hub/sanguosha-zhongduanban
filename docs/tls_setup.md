# WebSocket TLS (WSS) 部署指南

## 概述

三国杀 WebSocket 服务器默认使用 `ws://` 明文协议。**生产环境必须启用 TLS**，使用 `wss://` 加密传输。

推荐方案：**Nginx 反向代理 + Let's Encrypt 证书**，游戏服务器本身无需修改代码。

## 架构

```
客户端 ──wss://──> Nginx (:443) ──ws://──> 游戏服务器 (:8765)
                    │
               TLS 终止
               证书管理
```

## 步骤 1: 获取 TLS 证书

使用 Let's Encrypt（免费）或商业 CA。以 Certbot 为例：

```bash
sudo apt install certbot
sudo certbot certonly --standalone -d game.example.com
```

证书路径：
- 证书链: `/etc/letsencrypt/live/game.example.com/fullchain.pem`
- 私钥: `/etc/letsencrypt/live/game.example.com/privkey.pem`

## 步骤 2: Nginx 配置

文件: `/etc/nginx/sites-available/sanguosha`

```nginx
upstream sanguosha_ws {
    server 127.0.0.1:8765;
}

server {
    listen 443 ssl;
    server_name game.example.com;

    ssl_certificate     /etc/letsencrypt/live/game.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/game.example.com/privkey.pem;

    # TLS 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://sanguosha_ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 超时设置
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}

# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name game.example.com;
    return 301 https://$host$request_uri;
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/sanguosha /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 步骤 3: Docker Compose 集成

如果使用 Docker 部署，在 `docker-compose.prod.yml` 中添加 Nginx 服务：

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - game-server

  game-server:
    # 生产环境不暴露 8765 端口到宿主机
    expose:
      - "8765"
```

## 步骤 4: 客户端连接

客户端连接地址从 `ws://` 改为 `wss://`：

```python
# net/client.py 中修改连接地址
uri = "wss://game.example.com"
```

## 安全建议

1. **定期续期证书**: Let's Encrypt 证书 90 天过期，配置 cron 自动续期
   ```bash
   sudo certbot renew --quiet
   ```

2. **限制 WebSocket 端口**: 仅允许 Nginx 访问 8765 端口
   ```bash
   sudo ufw allow 443/tcp
   sudo ufw deny 8765/tcp
   ```

3. **启用 HSTS**: 在 Nginx 中添加
   ```nginx
   add_header Strict-Transport-Security "max-age=31536000" always;
   ```

4. **监控证书过期**: 添加告警或使用 `certbot certificates` 定期检查
