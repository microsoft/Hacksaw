cmake_minimum_required(VERSION 3.13.4)
project(drvmod)

set(CMAKE_CXX_STANDARD 14)

find_package(LLVM REQUIRED CONFIG)
add_definitions(${LLVM_DEFINITIONS})
include_directories(${LLVM_INCLUDE_DIRS})
link_directories(${LLVM_LIBRARY_DIRS})

add_subdirectory(busclass)
add_subdirectory(drvdevreg)
