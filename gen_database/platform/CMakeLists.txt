cmake_minimum_required (VERSION 3.0)
project (platformdb)

add_executable (platformdb buildplatform.cpp)

target_include_directories (platformdb PUBLIC
    "llvm-project/install/include")
target_link_directories (platformdb PUBLIC
    "llvm-project/install/lib")
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
    "llvm-project/install/include")
target_link_directories (callgraph PUBLIC
    "llvm-project/install/lib")
target_compile_options (callgraph PRIVATE
    "-D_GLIBCXX_USE_CXX11_ABI=1"
    )
target_link_libraries (callgraph LINK_PUBLIC
    LLVMCore
    LLVMSupport
    LLVMIRReader
    )
