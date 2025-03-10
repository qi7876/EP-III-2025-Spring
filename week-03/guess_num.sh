#!/bin/bash

# 生成1-100的随机数
target=$((RANDOM % 100 + 1))
count=0

echo "🎮 猜数字游戏开始！"
echo "我有一个1到100之间的数字，你能猜中吗？"
echo "输入 q 可以随时退出游戏"

while true; do
    read -p "➡️  请输入你的猜测（1-100）: " guess

    # 退出机制
    if [[ $guess == "q" ]]; then
        echo "🛑 游戏已退出，正确答案是 $target"
        exit 0
    fi

    # 输入验证
    if ! [[ $guess =~ ^[0-9]+$ ]]; then
        echo "❌ 错误：请输入有效的数字！"
        continue
    fi

    if ((guess < 1 || guess > 100)); then
        echo "⚠️ 注意：数字必须在1到100之间！"
        continue
    fi

    # 有效猜测计数
    ((count++))

    # 比较逻辑
    if ((guess < target)); then
        echo "📉 太小了！再试一次"
    elif ((guess > target)); then
        echo "📈 太大了！再试一次"
    else
        echo -e "\n🎉 恭喜！你在 $count 次尝试后猜中了正确答案 $target！"
        exit 0
    fi
done
