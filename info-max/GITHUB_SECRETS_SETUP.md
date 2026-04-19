# info_max GitHub Secrets 配置

在前端仓库 `Settings -> Secrets and variables -> Actions` 中配置以下内容。

本方案不依赖 DockerHub。GitHub Actions 会在 CI 中构建镜像，然后把镜像 tar.gz 包直接上传到服务器，再由服务器执行 `docker load`。

## 服务器

- `SERVER_HOST`
- `SERVER_USER`
- `SERVER_SSH_KEY`
- `SERVER_DEPLOY_PATH`
  - 例如：`/opt/info-max`

## GitHub Variables

- `VITE_API_BASE_URL`
  - 例如：`http://your-server-ip:8000`
  - 如果前面有反向代理，也可以填正式域名 API 地址
