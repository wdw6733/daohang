# 单页导航

这是一个公开模板，只有一个导航页、一个访问入口。Docker 应用、PT站和技术社区都放在同一页里，用分组和 tags 查找。

## 部署

先克隆整个仓库，不要只复制 `docker-compose.yml`。仓库里已有模板配置 `user-data/conf.yml`；启动时 `init-config` 会检查它是否存在，缺失时自动补一份默认配置并修正权限，已有配置不会被覆盖：

```bash
docker compose up -d
```

访问地址里的 `nas.local` 要换成你的 NAS IP 或域名。默认端口是 3000；要改端口时在部署目录建 `.env` 写 `DASHY_PORT=28888`，再用对应端口访问：

- 导航页：http://nas.local:3000

## 关键信息说明

公开仓库里只放占位，真实信息只改在你自己的部署目录里，不要提交回公开仓库。

| 占位 | 要改成什么 | 在哪里改 |
| --- | --- | --- |
| `nas.local` | 你的 NAS IP 或域名 | `user-data/conf.yml` 里的链接 |
| `router.local` | 你的软路由 IP 或域名 | `user-data/conf.yml` 里的软路由入口 |
| `8443` / `8081` / `8082` / `8083` | 示例端口，换成你的 NAS 管理、下载客户端、AI 网关和 Docker 应用端口 | `user-data/conf.yml` |
| `https://example.com/` | 你的 PT 站地址 | `user-data/conf.yml` 的 PT 分组 |
| `DASHY_PORT` | 本地访问端口，默认 3000 | 部署目录 `.env`，不要提交到公开仓库 |

不要把真实内网 IP、服务清单、账号、Cookie、passkey、API key 写进公开仓库。

## 镜像更新

镜像使用 `lissy93/dashy:latest`，并带 `pull_policy: always`。升级时拉最新仓库后重启即可，`up -d` 前会拉最新镜像：

```bash
git pull
docker compose down && docker compose up -d
```

仓库的 GitHub Actions 只负责保持 compose 里的 Dashy 标签为 `latest`。

## 状态检查策略

- Docker/NAS/软路由这类内网服务：开 `statusCheck: true`。
- PT 站和技术社区：保持 `statusCheck: false`。很多站有登录墙或 Cloudflare，容器探活容易误报。

## 安全边界

这套默认按内网/Tailscale 使用。模板没有开启登录鉴权，不要直接把 3000 端口转发到公网；要外网访问就放在反代鉴权或 Tailscale 后面。
