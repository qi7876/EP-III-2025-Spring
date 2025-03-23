#include "../include/output.hh"
#include <fstream>
#include <string>
#include <map>

// 输出到标准输出
void output_to_stdout(LIST list) {
    int length = list_length(list);
    for (int i = 0; i < length; i++) {
        printf("%d ", list_get(list, i));
    }
    printf("\n");
}

// 输出到文件
void output_to_file(LIST list, const char* filename) {
    FILE* fp = fopen(filename, "w");
    if (!fp) {
        fprintf(stderr, "Error: Could not open file %s for writing\n", filename);
        return;
    }

    int length = list_length(list);
    for (int i = 0; i < length; i++) {
        fprintf(fp, "%d\n", list_get(list, i));
    }
    fclose(fp);
}

// 输出到 CSV 文件
void output_to_csv(LIST list, const char* filename) {
    FILE* fp = fopen(filename, "w");
    if (!fp) {
        fprintf(stderr, "Error: Could not open file %s for writing\n", filename);
        return;
    }

    int length = list_length(list);
    for (int i = 0; i < length; i++) {
        fprintf(fp, "%d", list_get(list, i));
        if (i != length - 1) {
            fprintf(fp, ",");
        }
    }
    fprintf(fp, "\n");
    fclose(fp);
}

namespace {
// A simple TOML parser for key = "value" pairs (no sections, comments allowed)
std::map<std::string, std::string> parse_toml(const char* config_path) {
    std::map<std::string, std::string> config;
    std::ifstream infile(config_path);
    if (!infile.is_open()) {
        fprintf(stderr, "Error: Could not open config file %s\n", config_path);
        return config;
    }
    std::string line;
    while (std::getline(infile, line)) {
        // Remove spaces at beginning
        size_t start = line.find_first_not_of(" \t");
        if (start == std::string::npos) continue;
        // Skip comments and empty lines
        if (line[start] == '#' || line[start] == '\n') continue;
        // Find '='
        size_t eq = line.find('=', start);
        if (eq == std::string::npos) continue;
        std::string key = line.substr(start, eq - start);
        // Remove trailing spaces from key
        key.erase(key.find_last_not_of(" \t") + 1);
        std::string value = line.substr(eq + 1);
        // Trim spaces from value
        size_t vstart = value.find_first_not_of(" \t");
        if (vstart != std::string::npos)
            value = value.substr(vstart);
        // Remove surrounding quotes if present
        if (!value.empty() && value.front() == '"' && value.back() == '"') {
            value = value.substr(1, value.size() - 2);
        }
        config[key] = value;
    }
    return config;
}
} // end anonymous namespace

void output_to_email(LIST list, const char* config_path) {
    // 解析配置文件
    auto config = parse_toml(config_path);
    // 检查必须的参数是否都有
    if (config.find("to") == config.end() ||
        config.find("from") == config.end() ||
        config.find("server") == config.end() ||
        config.find("port") == config.end() ||
        config.find("auth") == config.end() ||
        config.find("auth_user") == config.end() ||
        config.find("auth_password") == config.end() ||
        config.find("body") == config.end()) {
        fprintf(stderr, "Error: Incomplete email configuration in %s\n", config_path);
        return;
    }

    int length = list_length(list);
    std::string list_str = "";
    for (int i = 0; i < length; i++) {
        list_str += std::to_string(list_get(list, i)) + " ";
    }

    // 使用 swaks 发送邮件，使用toml配置的参数
    char command[512];
    int port = atoi(config["port"].c_str());
    snprintf(command, sizeof(command),
        "swaks --to %s --from %s "
        "--server %s --port %d --auth %s "
        "--auth-user %s --auth-password \"%s\" --tls "
        "--body \"%s\" --attach \"%s\"",
        config["to"].c_str(), config["from"].c_str(),
        config["server"].c_str(), port, config["auth"].c_str(),
        config["auth_user"].c_str(), config["auth_password"].c_str(),
        config["body"].c_str(), list_str.c_str());
    // 执行 swaks 命令发送邮件
    int result = system(command);
    if (result != 0) {
        fprintf(stderr, "Error: Failed to send email\n");
    } else {
        printf("Email sent successfully to %s\n", config["to"].c_str());
    }
}
