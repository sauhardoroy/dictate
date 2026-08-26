cmake_minimum_required(VERSION 3.20)
project(Dictate VERSION 2.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Qt6
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets Network)
qt_standard_project_setup()

# Sources
set(PROJECT_SOURCES
    src/main.cpp
    src/config/settings.h
    src/ui/theme.h
    src/ui/liquid_glass_shader.h
    src/ui/pill.h
    src/ui/settings_dialog.h
    src/injection/typer.h
    src/punctuation/semantic_vad.h
    src/punctuation/voice_commands.h
    src/punctuation/post_processor.h
)

add_executable(Dictate WIN32 ${PROJECT_SOURCES})

target_link_libraries(Dictate PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
    Qt6::Network
    user32
    shell32
)

set_target_properties(Dictate PROPERTIES
    WIN32_EXECUTABLE TRUE
    OUTPUT_NAME "Dictate"
)
