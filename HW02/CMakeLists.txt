cmake_minimum_required(VERSION 3.10)

project(sort_linear_list)

# USE_LINKED: 是否使用链表实现
option(USE_LINKED "Use Linked List" OFF)
# USE_SEQUENTIAL: 是否使用顺序列表实现
option(USE_SEQUENTIAL "Use Sequential List" OFF)

if(USE_LINKED AND USE_SEQUENTIAL)
    message(FATAL_ERROR "Only one of USE_LINKED and USE_SEQUENTIAL can be enabled.")
endif()

# Default sources for the project
set(SOURCES src/main.cc src/input.cc src/sort.cc src/output.cc)

# If USE_SEQUENTIAL is enabled, add sequential list implementation
if(USE_SEQUENTIAL)
    list(APPEND SOURCES src/linear_list_sequential.cc)
else()
    # If USE_SEQUENTIAL is not enabled, use linked list implementation
    list(APPEND SOURCES src/linear_list_linked.cc)
endif()

# Define the executable for the main program
add_executable(${PROJECT_NAME} ${SOURCES})

# Include the "include" directory for header files
target_include_directories(${PROJECT_NAME} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

# Enable testing functionality
enable_testing()

# Define the executable for the test program
add_executable(test_main test/test_main.cc)

# Add the appropriate linear list source files to the test program
if(USE_SEQUENTIAL)
    target_sources(test_main PRIVATE src/linear_list_sequential.cc)
else()
    target_sources(test_main PRIVATE src/linear_list_linked.cc)
endif()

# Add common source files for the test program
target_sources(test_main PRIVATE src/sort.cc src/input.cc src/output.cc)

# Register the test with CTest
add_test(NAME TestBubbleSortFile COMMAND test_main --file test/data/input1.txt --sort bubble --stdout)
add_test(NAME TestQuickSortFile COMMAND test_main --file test/data/input2.txt --sort quick --stdout)
add_test(NAME TestMergeSortFile COMMAND test_main --file test/data/input3.txt --sort merge --stdout)
add_test(NAME TestBubbleSortCSV COMMAND test_main --csv test/data/input1.csv --sort bubble --stdout)
add_test(NAME TestQuickSortCSV COMMAND test_main --csv test/data/input2.csv --sort quick --stdout)
add_test(NAME TestMergeSortCSV COMMAND test_main --csv test/data/input3.csv --sort merge --stdout)
add_test(NAME TestBubbleSortStdin COMMAND test_main --stdin "5 3 8 1 2 7 4 6" --sort bubble --stdout)
add_test(NAME TestQuickSortStdin COMMAND test_main --stdin "10 20 30 40 50" --sort quick --stdout)
add_test(NAME TestMergeSortStdin COMMAND test_main --stdin "1 1 1 1 1" --sort merge --stdout)
