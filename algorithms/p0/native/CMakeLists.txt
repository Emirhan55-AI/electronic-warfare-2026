cmake_minimum_required(VERSION 3.20)
project(p0_channelizer_native LANGUAGES CXX)

add_library(p0_channelizer SHARED channelizer_native.cpp)
target_compile_features(p0_channelizer PRIVATE cxx_std_17)

if(MSVC)
  target_compile_options(p0_channelizer PRIVATE /O2 /fp:precise /arch:AVX2 /W4)
else()
  target_compile_options(p0_channelizer PRIVATE -O3 -mavx2 -mfma -Wall -Wextra -Wpedantic)
endif()
