# 线性表排序

## 要求

- [x] 基于linear_list.h 定义的线性表实现，并可在构造时指定顺序存储或链接存储等不同的构造方式；
- [x] 支持多种形式的输入，如标准输入、txt文本文件（一行一个数）、csv 文件（数之间采用逗号分隔），或支持注释的自定义格式文件，等等；
- [ ] 支持多种形式的输出，如标准输出、输出到文件、发送到邮件，等等；
- [ ] 支持多种不同的排序算法；
- [ ] 采用cmake编译机制，提供make test测试功能。

## 构建步骤

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

   二进制文件生成在 `build` 目录下，可以直接运行来进行测试。

## 使用方法

以下使用样例在项目`build`目录下运行。

```bash
# 进入标准输入交互模式
./sort_linear_list
./sort_linear_list --stdin
# I/O
Reading from standard input
[DEBUG] Using Linked List
1
2
3
4
5
2
3
1
4
EOF
Before Sorting:
List: 1 2 3 4 5 2 3 1 4 
After Sorting:
List: 1 1 2 2 3 3 4 4 5

# 参数转标准输入
./sort_linear_list --stdin "1 2 3 4 3 2 4 1"
# I/O
[DEBUG] Using Linked List
Before Sorting:
List: 1 2 3 4 3 2 4 1 
After Sorting:
List: 1 1 2 2 3 3 4 4

# pipeline兼容测试
echo "1 2 3 4 2 3 5 1 2" | ./sort_linear_list --stdin
# I/O
[DEBUG] Using Linked List
Before Sorting:
List: 1 2 3 4 2 3 5 1 2 
After Sorting:
List: 1 1 2 2 2 3 3 4 5

# file输入
./sort_linear_list --file ../test/list.txt
# I/O
[DEBUG] Using Linked List
Before Sorting:
List: 1 2 3 5 1 2 3 5 2 7 4 8 5 3 
After Sorting:
List: 1 1 2 2 2 3 3 3 4 5 5 5 7 8

# csv输入
./sort_linear_list --csv ../test/list.csv
# I/O
[DEBUG] Using Linked List
Before Sorting:
List: 1 4 5 6 4 7 1 3 4 7 4 1 
After Sorting:
List: 1 1 1 3 4 4 4 4 5 6 7 7
```

