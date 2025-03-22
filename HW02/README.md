# 线性表排序

## 要求

- [x] 基于linear_list.h 定义的线性表实现，并可在构造时指定顺序存储或链接存储等不同的构造方式；
- [ ] 支持多种形式的输入，如标准输入、txt文本文件（一行一个数）、csv 文件（数之间采用逗号分隔），或支持注释的自定义格式文件，等等；
- [ ] 支持多种形式的输出，如标准输出、输出到文件、发送到邮件，等等；
- [ ] 支持多种不同的排序算法；
- [ ] 采用cmake编译机制，提供make test测试功能。

## 使用方法

以下步骤在项目根目录进行

1. 通过 `cmake` 构建：

   1. 进入 `build` 目录下；

   2. 使用 `cmake` ：

      ```bash
      # 使用-DUSE_LINKED和-DUSE_SEQUENTIAL指定构造时使用的线性表实现方式
      # 二者只能使用其中一个
      # 如果不指定，则默认使用-DUSE_LINKED=ON
      cmake -DUSE_LINKED=ON ..
      cmake -DUSE_SEQUENTIAL=ON ..
      
      # 使用make编译
      make
      
      # 如果需要重新指定线性表实现方式，需要清理缓存
      # 第一种方式，清空build目录，接着再使用cmake
      rm -rf *
      cmake -DUSE_LINKED=ON ..
      # 第二种方式，使用-UUSE_LINKED和-UUSE_SEQUENTIAL刷新选项缓存
      cmake -UUSE_SEQUENTIAL -DUSE_LINKED=ON ..
      cmake -UUSE_LINKED -DUSE_SEQUENTIAL=ON ..
      
      # 再使用make编译
      make
      ```

2. 测试

   二进制文件生成在 `build` 目录下，可以直接运行来测试 `main.cc` 中给出的简单案例。