#include "../include/input.hh"
#include <fstream>
#include <sstream>
#include <iostream>
#include <cstdlib>

// 从 txt 文件中读取，每行一个数
LIST read_from_txt(const char* file_path) {
    LIST list = create_list();
    std::ifstream fin(file_path);
    if (!fin.is_open()) {
         std::cerr << "Error opening file: " << file_path << std::endl;
         return list;
    }
    int num;
    int pos = 0;
    while (fin >> num) { // 一行一个数
         list_insert(list, pos, num);
         pos++;
    }
    fin.close();
    return list;
}

// 从 csv 文件中读取，一行中使用逗号分隔
LIST read_from_csv(const char* file_path) {
    LIST list = create_list();
    std::ifstream fin(file_path);
    if (!fin.is_open()) {
         std::cerr << "Error opening file: " << file_path << std::endl;
         return list;
    }
    std::string line;
    if(std::getline(fin, line)) {
         std::istringstream iss(line);
         std::string token;
         int pos = 0;
         while (std::getline(iss, token, ',')) {
              int num = std::stoi(token);
              list_insert(list, pos, num);
              pos++;
         }
    }
    fin.close();
    return list;
}

// 从标准输入读取，支持管道输入或用户交互
LIST read_from_stdin() {
    LIST list = create_list();
    int num;
    int pos = 0;
    while(std::cin >> num) {
         list_insert(list, pos, num);
         pos++;
    }
    return list;
}