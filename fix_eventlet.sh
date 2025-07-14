#!/bin/bash

set -e  # 遇错退出
echo "🧹 正在卸载已有 eventlet..."
pip uninstall -y eventlet || true

echo "🧼 正在清除 pip 缓存..."
pip cache purge || true

echo "⬇️ 下载官方 eventlet==0.31.1 源码包..."
wget https://files.pythonhosted.org/packages/46/e9/c50d376b9c1fce0405fd12b22166b248f3d949f6a2c17122b4d1efb430dc/eventlet-0.31.1.tar.gz -O eventlet-0.31.1.tar.gz

echo "📦 解压源码..."
rm -rf eventlet-0.31.1
tar -xzf eventlet-0.31.1.tar.gz

echo "🚀 安装到当前 Python 环境..."
cd eventlet-0.31.1
python setup.py install

echo "✅ 安装完成，正在验证 ALREADY_HANDLED 是否可用..."
python -c "import eventlet.wsgi; print('✅ 是否包含 ALREADY_HANDLED:', hasattr(eventlet.wsgi, 'ALREADY_HANDLED'))"

echo "📂 当前 eventlet 安装路径："
python -c "import eventlet; print(eventlet.__file__)"

echo "🎉 完成！现在你可以重新运行 Ryu 控制器了。"

# 可选清理
cd ..
# rm -rf eventlet-0.31.1 eventlet-0.31.1.tar.gz
