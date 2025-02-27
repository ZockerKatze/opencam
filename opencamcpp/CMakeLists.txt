cmake_minimum_required(VERSION 3.16)
project(opencam LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

# Add OpenCV directory to CMAKE_PREFIX_PATH
list(APPEND CMAKE_PREFIX_PATH "/usr/local")

# Find Qt5
find_package(Qt5 COMPONENTS 
    Core 
    Gui 
    Widgets 
    Network
    REQUIRED
)

# Find OpenCV
find_package(OpenCV REQUIRED)
message(STATUS "OpenCV version: ${OpenCV_VERSION}")
message(STATUS "OpenCV libraries: ${OpenCV_LIBS}")
message(STATUS "OpenCV include dirs: ${OpenCV_INCLUDE_DIRS}")

# Check for CUDA support in OpenCV
if(";${OpenCV_LIBS};" MATCHES ";opencv_cudaimgproc;")
    message(STATUS "OpenCV CUDA support found")
    find_package(CUDA REQUIRED)
    enable_language(CUDA)
    set(CUDA_NVCC_FLAGS ${CUDA_NVCC_FLAGS};-O3)
    add_definitions(-DWITH_CUDA)
    set(HAS_CUDA TRUE)
else()
    message(STATUS "OpenCV was built without CUDA support. GPU acceleration will be disabled.")
    set(HAS_CUDA FALSE)
endif()

# Add source files
add_executable(${PROJECT_NAME} 
    main.cpp
)

# Link libraries
target_link_libraries(${PROJECT_NAME} PRIVATE
    Qt5::Core
    Qt5::Gui
    Qt5::Widgets
    Qt5::Network
    ${OpenCV_LIBS}
)

if(HAS_CUDA)
    target_link_libraries(${PROJECT_NAME} PRIVATE
        ${CUDA_LIBRARIES}
    )
endif()

# Include directories
target_include_directories(${PROJECT_NAME} PRIVATE
    ${OpenCV_INCLUDE_DIRS}
)

if(HAS_CUDA)
    target_include_directories(${PROJECT_NAME} PRIVATE
        ${CUDA_INCLUDE_DIRS}
    )
endif()

# Installation rules
install(TARGETS ${PROJECT_NAME}
    RUNTIME DESTINATION bin
    COMPONENT applications
)

# Function to safely install a library and its dependencies
function(install_library lib_path)
    if(EXISTS "${lib_path}")
        file(REAL_PATH "${lib_path}" real_path)
        install(FILES "${real_path}"
            DESTINATION lib
            COMPONENT libraries
        )
        
        # Get library dependencies
        execute_process(
            COMMAND ldd "${real_path}"
            OUTPUT_VARIABLE LDD_OUTPUT
        )
        
        # Extract and install dependencies
        string(REGEX MATCHALL "/[^)]*\\.so[^)]*" DEPS "${LDD_OUTPUT}")
        foreach(dep ${DEPS})
            if(EXISTS "${dep}" AND NOT "${dep}" MATCHES "^/lib" AND NOT "${dep}" MATCHES "^/usr/lib")
                install(FILES "${dep}"
                    DESTINATION lib
                    COMPONENT libraries
                )
            endif()
        endforeach()
    endif()
endfunction()

# Install OpenCV libraries
foreach(lib ${OpenCV_LIBS})
    get_target_property(lib_location ${lib} LOCATION)
    if(lib_location)
        install_library("${lib_location}")
    endif()
endforeach()

# Install Qt plugins
if(Qt5_DIR)
    file(GLOB_RECURSE QT_PLUGINS "${Qt5_DIR}/../../../plugins/*.so")
    foreach(plugin ${QT_PLUGINS})
        get_filename_component(plugin_path "${plugin}" DIRECTORY)
        get_filename_component(plugin_dir "${plugin_path}" NAME)
        install(FILES "${plugin}"
            DESTINATION plugins/${plugin_dir}
            COMPONENT plugins
        )
    endforeach()
endif()

# Print configuration summary
message(STATUS "")
message(STATUS "Configuration Summary")
message(STATUS "--------------------")
message(STATUS "OpenCV version: ${OpenCV_VERSION}")
message(STATUS "CUDA support: ${HAS_CUDA}")
message(STATUS "Qt version: ${Qt5_VERSION}")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ compiler: ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "Installation prefix: ${CMAKE_INSTALL_PREFIX}")
message(STATUS "") 