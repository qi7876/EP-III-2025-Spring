#include "../include/input.hh"
#include "../include/linear_list.hh"
#include "../include/output.hh"
#include "../include/sort.hh"
#include <cstdio>
#include <iostream>
#include <ostream>
#include <sstream>
#include <cstring>

// Function to display detailed help information
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

int main(int argc, char* argv[]) {
    LIST myList = nullptr;
    std::string sort_algorithm = "";

    // Input options
    bool use_stdin = false;
    bool use_file = false;
    bool use_csv = false;
    char* input_path = nullptr;
    std::string stdin_arg;

    // Output options
    bool use_stdout = false;
    bool use_out_file = false;
    bool use_out_csv = false;
    bool use_email = false;
    char* output_path = nullptr;

    // Email option (now a configuration file path)
    const char* email_config_path = nullptr;

    // Help flag
    bool show_help = false;

    // Add error tracking
    bool parse_error = false;
    std::string error_message;

    // Using a simpler approach for parsing arguments
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            show_help = true;
        } else if (strcmp(argv[i], "--stdin") == 0) {
            use_stdin = true;
            if (i + 1 < argc && argv[i + 1][0] != '-') {
                stdin_arg = argv[i + 1];
                i++; // Skip the next argument as we've consumed it
            }
        } else if (strcmp(argv[i], "--file") == 0) {
            if (i + 1 < argc) {
                use_file = true;
                input_path = argv[i + 1];
                i++; // Skip the next argument
            } else {
                parse_error = true;
                error_message = "Error: --file requires a file path";
                break;
            }
        } else if (strcmp(argv[i], "--csv") == 0) {
            if (i + 1 < argc) {
                use_csv = true;
                input_path = argv[i + 1];
                i++; // Skip the next argument
            } else {
                parse_error = true;
                error_message = "Error: --csv requires a file path";
                break;
            }
        } else if (strcmp(argv[i], "--stdout") == 0) {
            use_stdout = true;
        } else if (strcmp(argv[i], "--out-file") == 0) {
            if (i + 1 < argc) {
                use_out_file = true;
                output_path = argv[i + 1];
                i++; // Skip the next argument
            } else {
                parse_error = true;
                error_message = "Error: --out-file requires a file path";
                break;
            }
        } else if (strcmp(argv[i], "--out-csv") == 0) {
            if (i + 1 < argc) {
                use_out_csv = true;
                output_path = argv[i + 1];
                i++; // Skip the next argument
            } else {
                parse_error = true;
                error_message = "Error: --out-csv requires a file path";
                break;
            }
        } else if (strcmp(argv[i], "--sort") == 0) {
            if (i + 1 < argc) {
                sort_algorithm = argv[i + 1];
                i++;
            } else {
                parse_error = true;
                error_message = "Error: --sort requires an algorithm name";
                break;
            }
        } else if (strcmp(argv[i], "--email") == 0) {
            if (i + 1 < argc) {
                use_email = true;
                email_config_path = argv[i + 1];
                i++;
            } else {
                parse_error = true;
                error_message = "Error: --email requires a configuration file path";
                break;
            }
        } else {
            parse_error = true;
            error_message = std::string("Unknown option: ") + argv[i];
            break;
        }
    }

    // Check if help was requested
    if (show_help) {
        display_help(argv[0]);
        return 0;
    }

    // Check for errors in argument parsing
    if (parse_error) {
        std::cerr << error_message << std::endl;
        std::cerr << "Usage: " << argv[0] << " [--stdin [arg]] [--file path] [--csv path] [--stdout] [--out-file path] [--out-csv path] [--email config_path] [--sort method]" << std::endl;
        std::cerr << "Use --help or -h for more detailed usage information" << std::endl;
        return 1;
    }

    // Validate input options - ensure only one input method is selected
    int input_count = (use_stdin ? 1 : 0) + (use_file ? 1 : 0) + (use_csv ? 1 : 0);
    if (input_count > 1) {
        fprintf(stderr, "Error: Only one input method can be specified\n");
        return 1;
    }
    int output_count = (use_stdout ? 1 : 0) + (use_out_file ? 1 : 0) + (use_out_csv ? 1 : 0) + (use_email ? 1 : 0);

    // Default to stdin if no input option is provided
    if (input_count == 0) {
        use_stdin = true;
    }

    // Default to stdout if no output option is provided
    if (output_count == 0) {
        use_stdout = true;
    }

    // Process input based on selected option
    if (use_stdin) {
        if (!stdin_arg.empty()) {
            std::istringstream iss(stdin_arg);
            std::streambuf* orig = std::cin.rdbuf();
            std::cin.rdbuf(iss.rdbuf());
            myList = read_from_stdin();
            std::cin.rdbuf(orig); // Restore standard input
        } else {
            myList = read_from_stdin();
        }
    } else if (use_file) {
        myList = read_from_txt(input_path);
    } else if (use_csv) {
        myList = read_from_csv(input_path);
    }

    // Before processing output, ensure myList is not nullptr
    if (myList == nullptr) {
        fprintf(stderr, "Error: No valid input data was read\n");
        return 1;
    }

    if (sort_algorithm == "bubble" || sort_algorithm.empty()) {
        bubble_sort_list(myList);
    } else if (sort_algorithm == "quick") {
        quick_sort_list(myList);
    } else if (sort_algorithm == "merge") {
        merge_sort_list(myList);
    } else {
        std::cout << "Invalid sort algorithm. Use bubble sort instead." << std::endl;
        bubble_sort_list(myList);
    }

    // Process output based on selected option
    if (use_stdout) {
        output_to_stdout(myList);
    }
    if (use_out_file) {
        output_to_file(myList, output_path);
    }
    if (use_out_csv) {
        output_to_csv(myList, output_path);
    }
    if (use_email) {
        output_to_email(myList, email_config_path); // Send email using TOML configuration
    }

    return 0;
}
