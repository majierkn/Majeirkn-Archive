cmake_minimum_required(VERSION 3.22.1)
project(majeirkn)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# O código do llama.cpp é obtido separadamente conforme README.md.
if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/llama.cpp/CMakeLists.txt")
    message(FATAL_ERROR "llama.cpp não encontrado. Siga README.md para clonar a dependência.")
endif()

set(LLAMA_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_SERVER OFF CACHE BOOL "" FORCE)
set(GGML_OPENMP OFF CACHE BOOL "" FORCE)
add_subdirectory(llama.cpp llama-build)

add_library(majeirkn SHARED native-lib.cpp)
target_include_directories(majeirkn PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/llama.cpp/include")
target_link_libraries(majeirkn PRIVATE llama android log)
