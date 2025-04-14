#!/usr/bin/env python3
from llama_cpp import Llama
import sys

if len(sys.argv) != 2:
    print("用法: python chat.py <模型路径>")
    sys.exit(1)

model_path = sys.argv[1]
llm = Llama(model_path=model_path, n_ctx=2048, n_gpu_layers=-1)
print("模型加载完成！输入 'exit' 退出。")

while True:
    user_input = input("你: ")
    if user_input.lower() == "exit":
        break
    output = llm(user_input, max_tokens=512, temperature=0.7)
    print("AI:", output["choices"][0]["text"])
