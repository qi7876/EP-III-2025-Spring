cmake_minimum_required(VERSION 3.10)

project(sort_linear_list)

# USE_LINKED: 是否使用链表实现
option(USE_LINKED "Use Linked List" OFF)
# USE_SEQUENTIAL: 是否使用顺序列表实现
option(USE_SEQUENTIAL "Use Sequential List" OFF)

if(USE_LINKED AND USE_SEQUENTIAL)
  message(FATAL_ERROR "Only one of USE_LINKED and USE_SEQUENTIAL can be enabled.")
endif()

set(SOURCES src/main.cc src/input.cc)

if(USE_SEQUENTIAL)
  list(APPEND SOURCES src/linear_list_sequential.cc)
else()
  list(APPEND SOURCES src/linear_list_linked.cc)
endif()

add_executable(${PROJECT_NAME} ${SOURCES})

target_include_directories(${PROJECT_NAME} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
