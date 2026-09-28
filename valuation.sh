#!/bin/bash

# ==============================================================================
# 本地估值平台后台服务管理脚本
# 用法: ./valuation.sh {start|stop|restart|status|logs}
# ==============================================================================

# 项目目录配置
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$APP_DIR/valuation.pid"
LOG_FILE="$APP_DIR/valuation.log"
VENV_ACTIVATE="$APP_DIR/valuation_env/bin/activate"
PORT=8501

# 检查虚拟环境
activate_env() {
    if [ -f "$VENV_ACTIVATE" ]; then
        source "$VENV_ACTIVATE"
    else
        echo "⚠️  未找到虚拟环境 $VENV_ACTIVATE，将使用系统默认 Python 环境。"
    fi
}

# 启动服务
start() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "❌ 服务已经在运行中，PID: $(cat "$PID_FILE")"
        echo "🔗 访问地址: http://localhost:$PORT"
        return 1
    fi

    echo "🚀 正在启动本地估值服务..."
    activate_env

    # 在后台启动 Streamlit 并将日志重定向到文件
    nohup streamlit run "$APP_DIR/app.py" \
        --server.port=$PORT \
        --server.headless=true \
        --browser.gatherUsageStats=false \
        > "$LOG_FILE" 2>&1 &

    # 保存 PID
    echo $! > "$PID_FILE"
    
    # 验证启动状态
    sleep 2
    if kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "✅ 服务启动成功！"
        echo "📌 PID: $(cat "$PID_FILE")"
        echo "🌐 访问地址: http://localhost:$PORT"
        echo "📝 日志文件: $LOG_FILE"
    else
        echo "❌ 服务启动失败，请检查日志: $LOG_FILE"
        rm -f "$PID_FILE"
    fi
}

# 关闭服务
stop() {
    if [ ! -f "$PID_FILE" ] || ! kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "⚠️  服务未在运行。"
        rm -f "$PID_FILE"
        return 0
    fi

    PID=$(cat "$PID_FILE")
    echo "🛑 正在停止估值服务 (PID: $PID)..."
    
    # 优雅杀死主进程及子进程
    kill $PID
    
    # 等待最多 10 秒退出
    for i in {1..10}; do
        if ! kill -0 $PID 2>/dev/null; then
            break
        fi
        sleep 1
    done

    # 如果仍然在运行，强制杀进程
    if kill -0 $PID 2>/dev/null; then
        echo "⚠️  服务未响应，正在强制关闭..."
        kill -9 $PID 2>/dev/null
    fi

    rm -f "$PID_FILE"
    echo "✅ 服务已成功关闭。"
}

# 查看状态
status() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "🟢 服务运行中 | PID: $(cat "$PID_FILE") | 端口: $PORT"
        echo "🔗 访问地址: http://localhost:$PORT"
    else
        echo "🔴 服务未运行。"
        rm -f "$PID_FILE" 2>/dev/null
    fi
}

# 查看实时日志
logs() {
    if [ -f "$LOG_FILE" ]; then
        echo "📖 正在实时查看服务日志 (按 Ctrl+C 退出):"
        tail -f "$LOG_FILE"
    else
        echo "❌ 未找到日志文件 $LOG_FILE"
    fi
}

# 命令行入口调度
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 1
        start
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    *)
        echo "使用说明: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
