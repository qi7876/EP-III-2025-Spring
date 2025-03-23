#include "../include/linear_list.hh"
#include "../include/sort.hh"
#include "../include/input.hh"
#include "../include/output.hh"
#include <cassert>
#include <iostream>
#include <vector>
#include <algorithm>  // 用于 std::sort
#include <sstream>    // 用于 std::istringstream
#include <fstream>    // 用于文件操作
#include <random>     // 用于生成随机数
#include <cstdlib>    // 用于 std::system
#include <cstring>

// 打印列表内容（用于调试）
void print_list(LIST list) {
    std::cout << "List: ";
    for (int i = 0; i < list_length(list); i++) {
        std::cout << list_get(list, i) << " ";
    }
    std::cout << std::endl;
}

void display_help(const char* program_name) {
    std::cout << "Usage: " << program_name << " [OPTIONS]" << std::endl;
    std::cout << "\nInput Options:" << std::endl;
    std::cout << "  --stdin [arg]    Read input from standard input or use provided string as input" << std::endl;
    std::cout << "  --file PATH      Read input from specified text file" << std::endl;
    std::cout << "  --csv PATH       Read input from specified CSV file" << std::endl;
    std::cout << "  --sort METHOD    You can choose bubble, quick or merge sort" << std::endl;
    std::cout << "\nOutput Options:" << std::endl;
    std::cout << "  --stdout         Display output to standard output (default)" << std::endl;
    std::cout << "  --out-file PATH  Write output to specified text file" << std::endl;
    std::cout << "  --out-csv PATH   Write output to specified CSV file" << std::endl;
    std::cout << "  --email CONFIG_PATH  Send email with the sorted list using the specified TOML configuration file" << std::endl;
    std::cout << "\nOther Options:" << std::endl;
    std::cout << "  --help, -h       Display this help message and exit" << std::endl;
    std::cout << "\nNotes:" << std::endl;
    std::cout << "  - Only one input and one output option can be specified" << std::endl;
    std::cout << "  - If no input option is provided, stdin is used by default" << std::endl;
    std::cout << "  - If no output option is provided, stdout is used by default" << std::endl;
}


// 测试排序函数
void test_sort(LIST list, const char* sort_algorithm) {
    // 调用排序函数
    if (strcmp(sort_algorithm, "bubble") == 0) {
        bubble_sort_list(list);
    } else if (strcmp(sort_algorithm, "quick") == 0) {
        quick_sort_list(list);
    } else if (strcmp(sort_algorithm, "merge") == 0) {
        merge_sort_list(list);
    } else {
        std::cerr << "Error: Unknown sort algorithm " << sort_algorithm << std::endl;
        return;
    }

    // 验证排序结果是否正确
    std::vector<int> data;
    for (int i = 0; i < list_length(list); i++) {
        data.push_back(list_get(list, i));
    }

    std::vector<int> sorted_data = data;
    std::sort(sorted_data.begin(), sorted_data.end());

    assert(data == sorted_data);
    std::cout << "Sort test passed!\n";
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " [OPTIONS]" << std::endl;
        return 1;
    }

    LIST list = nullptr;
    const char* sort_algorithm = "bubble";  // 默认排序算法
    bool use_stdout = true;  // 默认输出到标准输出

    // 解析命令行参数
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--stdin") == 0) {
            if (i + 1 < argc && argv[i + 1][0] != '-') {
                std::istringstream iss(argv[i + 1]);
                std::streambuf* orig = std::cin.rdbuf();
                std::cin.rdbuf(iss.rdbuf());
                list = read_from_stdin();
                std::cin.rdbuf(orig);
                i++;
            } else {
                list = read_from_stdin();
            }
        } else if (strcmp(argv[i], "--file") == 0) {
            if (i + 1 < argc) {
                list = read_from_txt(argv[i + 1]);
                i++;
            } else {
                std::cerr << "Error: --file requires a file path" << std::endl;
                return 1;
            }
        } else if (strcmp(argv[i], "--csv") == 0) {
            if (i + 1 < argc) {
                list = read_from_csv(argv[i + 1]);
                i++;
            } else {
                std::cerr << "Error: --csv requires a file path" << std::endl;
                return 1;
            }
        } else if (strcmp(argv[i], "--sort") == 0) {
            if (i + 1 < argc) {
                sort_algorithm = argv[i + 1];
                i++;
            } else {
                std::cerr << "Error: --sort requires an algorithm name" << std::endl;
                return 1;
            }
        } else if (strcmp(argv[i], "--stdout") == 0) {
            use_stdout = true;
        } else if (strcmp(argv[i], "--out-file") == 0) {
            if (i + 1 < argc) {
                output_to_file(list, argv[i + 1]);
                i++;
            } else {
                std::cerr << "Error: --out-file requires a file path" << std::endl;
                return 1;
            }
        } else if (strcmp(argv[i], "--out-csv") == 0) {
            if (i + 1 < argc) {
                output_to_csv(list, argv[i + 1]);
                i++;
            } else {
                std::cerr << "Error: --out-csv requires a file path" << std::endl;
                return 1;
            }
        } else if (strcmp(argv[i], "--email") == 0) {
            if (i + 1 < argc) {
                output_to_email(list, argv[i + 1]);
                i++;
            } else {
                std::cerr << "Error: --email requires a configuration file path" << std::endl;
                return 1;
            }
        } else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            display_help(argv[0]);
            return 0;
        } else {
            std::cerr << "Error: Unknown option " << argv[i] << std::endl;
            return 1;
        }
    }

    if (list == nullptr) {
        std::cerr << "Error: No valid input data was read" << std::endl;
        return 1;
    }

    // 调用排序函数
    test_sort(list, sort_algorithm);

    // 输出结果
    if (use_stdout) {
        output_to_stdout(list);
    }

    // 销毁列表
    list_destroy(list);

    return 0;
}