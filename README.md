# 单容器导航页

这是公开脱敏版：把 Dashy 的链接库能力和 Homepage 式状态面板合并成一个容器。仓库里只放占位，真实 PT 站、NetBird peer 名称和内网地址只改在自己的部署目录，不要提交回公开仓库。

## 启动

```bash

docker compose up -d
```

默认端口 `28888`。如果端口被占用，在 `.env` 写 `NAV_PORT=28889`。

本地设置放在 `local-config/config.json`，镜像更新不会覆盖它。旧 Dashy 设置可迁移：

```bash
python3 migrate-dashy.py user-data/conf.yml local-config/config.json
docker compose up -d
```

## 关键信息说明

| 占位 | 要改成什么 | 在哪里改 |
| --- | --- | --- |
| `example.com` | 你的 PT 站地址 | `site/index.html` 的 `PT_SITES` |
| `10.99.0.10` 等 | 你的 NetBird peer IP | `site/index.html` 的 `PEER_META` 和拓扑文字 |
| `NAV_PORT` | 本地访问端口，默认 28888 | 部署目录 `.env` |

## 真实流量

容器内每 2 秒通过 Docker socket 执行 `docker exec netbird netbird status`，读取 RX/TX 计数器并计算 Mbps。蓝色是接收，绿色是发送。没有真实数据时页面显示未连接采集器，不生成假流量。

注意：挂载 Docker socket 是为了读取现有 NetBird 容器的状态；这个导航容器只建议放在内网/Tailscale/NetBird 内使用，不要直接暴露公网。

## 容器内网/公网

“我的容器”区由浏览器添加并保存在本机浏览器。自动模式先探内网地址，通则走内网，不通走公网；也可以手动切内网/公网。
