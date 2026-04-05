#!/usr/bin/env bash
# 入口脚本：与 setup_venv_fedora.sh 相同，在 WSL / Linux 下创建 .venv 并安装项目
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/setup_venv_fedora.sh" "$@"
