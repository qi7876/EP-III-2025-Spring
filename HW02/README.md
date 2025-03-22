# 线性表排序

## 要求

- [x] 基于 linear_list.h 定义的线性表实现，并可在构造时指定顺序存储或链接存储等不同的构造方式；
- [x] 支持多种形式的输入，如标准输入、txt 文本文件 (一行一个数)、csv 文件 (数之间采用逗号分隔)，或支持注释的自定义格式文件，等等；
- [x] 支持多种形式的输出，如标准输出、输出到文件、发送到邮件，等等；
- [ ] 支持多种不同的排序算法；
- [ ] 采用 cmake 编译机制，提供 make test 测试功能。

## 构建步骤

以下步骤在项目根目录进行

1. 通过 `cmake` 构建：

   1. 进入 `build` 目录下；

   2. 使用 `cmake`：

      ```bash
      # 使用 -DUSE_LINKED 和 -DUSE_SEQUENTIAL 指定构造时使用的线性表实现方式
      # 二者只能使用其中一个
      # 如果不指定，则默认使用 -DUSE_LINKED=ON
      cmake -DUSE_LINKED=ON ..
      cmake -DUSE_SEQUENTIAL=ON ..
      
      # 使用 make 编译
      make
      
      # 如果需要重新指定线性表实现方式，需要清理缓存
      # 第一种方式，清空 build 目录，接着再使用 cmake
      rm -rf *
      cmake -DUSE_LINKED=ON ..
      # 第二种方式，使用 -UUSE_LINKED 和 -UUSE_SEQUENTIAL 刷新选项缓存
      cmake -UUSE_SEQUENTIAL -DUSE_LINKED=ON ..
      cmake -UUSE_LINKED -DUSE_SEQUENTIAL=ON ..
      
      # 再使用 make 编译
      make
      ```

2. 测试

   二进制文件生成在 `build` 目录下，可以直接运行来进行测试。

## 使用方法

以下使用样例在项目 `build` 目录下运行。

### 帮助

```bash
# 处理错误未知 flag
./sort_linear_list --error
# I/O
Unknown option: --error
Usage: ./sort_linear_list [--stdin [arg]] [--file path] [--csv path] [--stdout] [--out-file path] [--out-csv path]
Use --help or -h for more detailed usage information

# 展示详细用法
./sort_linear_list --help
# I/O
Usage: ./sort_linear_list [OPTIONS]

Input Options:
  --stdin [arg]    Read input from standard input or use provided string as input
  --file PATH      Read input from specified text file
  --csv PATH       Read input from specified CSV file

Output Options:
  --stdout         Display output to standard output (default)
  --out-file PATH  Write output to specified text file
  --out-csv PATH   Write output to specified CSV file

Other Options:
  --help, -h       Display this help message and exit

Notes:
  - Only one input and one output option can be specified
  - If no input option is provided, stdin is used by default
  - If no output option is provided, stdout is used by default
```



### 输入样例

```bash
# 进入标准输入交互模式
./sort_linear_list
./sort_linear_list --stdin
# I/O
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
1 1 2 2 3 3 4 4 5

# 参数转标准输入
./sort_linear_list --stdin "1 2 3 4 3 2 4 1"
# I/O
1 1 2 2 3 3 4 4

# pipeline 兼容测试
echo "1 2 3 4 2 3 5 1 2" | ./sort_linear_list --stdin
# I/O
1 1 2 2 2 3 3 4 5

# file 输入
./sort_linear_list --file ../test/list.txt
# I/O
1 1 2 2 2 3 3 3 4 5 5 5 7 8

# csv 输入
./sort_linear_list --csv ../test/list.csv
# I/O
1 1 1 3 4 4 4 4 5 6 7 7
```

### 输出样例

```bash
# 输出到标准输出
./sort_linear_list --stdin "1 2 3 4 3 2 4 1"
./sort_linear_list --stdin "1 2 3 4 3 2 4 1" --stdout
# I/O
1 1 2 2 3 3 4 4

# 输出到文件
./sort_linear_list --stdin "1 2 3 4 3 2 4 1" --out-file ../test/list_out.txt; cat ../test/list_out.txt
# I/O
1
1
2
2
3
3
4
4


# 输出到 csv
./sort_linear_list --stdin "1 2 3 4 3 2 4 1" --out-csv ../test/list_out.csv; cat ../test/list_out.csv
# I/O
1,1,2,2,3,3,4,4

```

