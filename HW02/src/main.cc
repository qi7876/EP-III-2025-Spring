#include "../include/linear_list.hh"
#include "../include/input.hh"
#include <iostream>
#include <stdio.h>
#include <string>
#include <cstring>
#include <sstream>

void bubble_sort_list(LIST list) {
    if (list == nullptr) {
        return;
    }

    int length = list_length(list);
    if (length <= 1) {
        return;
    }

    for (int i = 0; i < length - 1; i++) {
        for (int j = 0; j < length - i - 1; j++) {
            int val1 = list_get(list, j);
            int val2 = list_get(list, j + 1);

            if (val1 > val2) {
                // 正确的交换实现：先删除两个节点，再按顺序插入交换后的数据
                list_delete(list, j);
                list_delete(list, j); // 第一个删除后，后面的元素前移
                list_insert(list, j, val1);
                list_insert(list, j, val2);
            }
        }
    }
}

void print_list(LIST list) {
    int length = list_length(list);
    printf("List: ");
    for (int i = 0; i < length; i++) {
        printf("%d ", list_get(list, i));
    }
    printf("\n");
}

int main(int argc, char *argv[]) {
    LIST myList = nullptr;
    
    // 根据 flag 选择输入方式
    if (argc < 2) {
         // 无flag时，默认使用标准输入（管道或交互）
         printf("Reading from standard input\n");
         myList = read_from_stdin();
    } else if (strcmp(argv[1], "--file") == 0) {
         if (argc < 3) {
             fprintf(stderr, "Error: --file requires a file path\n");
             return 1;
         }
         myList = read_from_txt(argv[2]);
    } else if (strcmp(argv[1], "--csv") == 0) {
         if (argc < 3) {
             fprintf(stderr, "Error: --csv requires a file path\n");
             return 1;
         }
         myList = read_from_csv(argv[2]);
    } else if (strcmp(argv[1], "--stdin") == 0) {
         if (argc >= 3) {
             // 如果存在参数，将参数转换为标准输入
             std::istringstream iss(argv[2]);
             std::streambuf *orig = std::cin.rdbuf();
             std::cin.rdbuf(iss.rdbuf());
             myList = read_from_stdin();
             std::cin.rdbuf(orig); // 恢复标准输入
         } else {
             myList = read_from_stdin();
         }
    } else {
         fprintf(stderr, "Unknown flag: %s\n", argv[1]);
         return 1;
    }
    
    printf("Before Sorting:\n");
    print_list(myList);
    bubble_sort_list(myList);
    printf("After Sorting:\n");
    print_list(myList);

    return 0;
}