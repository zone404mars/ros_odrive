cmake_minimum_required(VERSION 3.8)
project(odrive_rob_accueil)

find_package(ament_cmake REQUIRED)

# Paquet de bringup : pas de code compile, seulement launch/urdf/config a installer.
install(
  DIRECTORY launch config urdf
  DESTINATION share/${PROJECT_NAME}
)

# Noeud teleop clavier : script Python lancable via ros2 run.
install(PROGRAMS
  scripts/teleop_arrows.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
