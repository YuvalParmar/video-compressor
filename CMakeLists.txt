cmake_minimum_required(VERSION 3.18)
project(semantic_codec LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

find_package(Python COMPONENTS Interpreter Development REQUIRED)
find_package(OpenCV REQUIRED COMPONENTS core imgproc imgcodecs)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(semantic_codec src/bindings.cpp src/codec_engine.cpp)
target_include_directories(semantic_codec PRIVATE ${OpenCV_INCLUDE_DIRS} src)
target_link_libraries(semantic_codec PRIVATE ${OpenCV_LIBS})

if(MSVC)
  target_compile_options(semantic_codec PRIVATE /O2 /EHsc)
else()
  target_compile_options(semantic_codec PRIVATE -O3 -Wall -Wextra)
endif()
