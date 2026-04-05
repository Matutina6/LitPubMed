#!/usr/bin/env bash
# WSL / Linux：在项目根目录创建 .venv 并以可编辑方式安装 LitPubMed
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "未找到 python3。WSL 示例: sudo apt install python3 python3-pip python3-venv" >&2
  exit 1
fi

python3 -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate
python -m pip install -U pip wheel
pip install -e ".[dev]"

echo ""
echo "下一步:"
echo "  source .venv/bin/activate"
echo "  cp .env.example .env   # 填入百炼 / DashScope API Key"
echo "  litpubmed              # 或 litpubmed-api"
