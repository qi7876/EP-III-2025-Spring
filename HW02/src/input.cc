#include "../include/input.hh"
#include <fstream>
#include <iostream>
#include <sstream>

LIST read_from_txt(const char* file_path) {
    LIST list = create_list();
    std::ifstream fin(file_path);
    if (!fin.is_open()) {
        std::cerr << "Error opening file: " << file_path << std::endl;
        return list;
    }
    int num;
    int pos = 0;
    while (fin >> num) {
        list_insert(list, pos, num);
        pos++;
    }
    fin.close();
    return list;
}

LIST read_from_csv(const char* file_path) {
    LIST list = create_list();
    std::ifstream fin(file_path);
    if (!fin.is_open()) {
        std::cerr << "Error opening file: " << file_path << std::endl;
        return list;
    }
    std::string line;
    if (std::getline(fin, line)) {
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

LIST read_from_stdin() {
    LIST list = create_list();
    int num;
    int pos = 0;
    while (std::cin >> num) {
        list_insert(list, pos, num);
        pos++;
    }
    return list;
}