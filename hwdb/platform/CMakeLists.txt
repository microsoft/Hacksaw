cmake_minimum_required (VERSION 3.13.4)
project (platformdb)

add_executable (platformdb buildplatform.cpp)

target_include_directories (platformdb PUBLIC
    "${LLVM_INCLUDE_PATH}")
target_link_directories (platformdb PUBLIC
    "${LLVM_LIB_PATH}")
target_compile_options (platformdb PRIVATE
    "-D_GLIBCXX_USE_CXX11_ABI=1"
    )
target_link_libraries (platformdb LINK_PUBLIC
    LLVMCore
    LLVMSupport
    LLVMIRReader
    )

add_executable (callgraph buildcallgraph.cpp)

target_include_directories (callgraph PUBLIC
    "${LLVM_INCLUDE_PATH}")
target_link_directories (callgraph PUBLIC
    "${LLVM_LIB_PATH}")
target_compile_options (callgraph PRIVATE
    "-D_GLIBCXX_USE_CXX11_ABI=1"
    )
target_link_libraries (callgraph LINK_PUBLIC
    LLVMCore
    LLVMSupport
    LLVMIRReader
    )
