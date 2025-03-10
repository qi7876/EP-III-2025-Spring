cmake_minimum_required(VERSION 3.10)

project(es-helloworld)
add_executable(${PROJECT_NAME} "main.c")
INSTALL( TARGETS ${PROJECT_NAME} RUNTIME DESTINATION bin)
