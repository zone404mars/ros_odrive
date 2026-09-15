# Lancement de la base mobile du robot d'accueil (ODrive ros2_control).
# Deux phases via l'argument start_base_controller :
#   false (defaut) : seul joint_state_broadcaster, lecture du feedback, roues libres.
#   true           : ajoute diff_drive_base_controller, pilotage en vitesse.

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Arguments de lancement.
    declared_arguments = [
        DeclareLaunchArgument(
            "use_mock_hardware", default_value="false",
            description="Materiel simule (sans ODrive ni CAN) si true."),
        DeclareLaunchArgument(
            "start_base_controller", default_value="false",
            description="Phase 2 : demarre le pilotage vitesse (diff_drive) si true."),
    ]
    use_mock_hardware = LaunchConfiguration("use_mock_hardware")
    start_base_controller = LaunchConfiguration("start_base_controller")

    pkg = FindPackageShare("odrive_rob_accueil")

    # URDF genere par xacro ; use_mock_hardware est transmis a la macro ros2_control.
    robot_description_content = Command([
        FindExecutable(name="xacro"), " ",
        PathJoinSubstitution([pkg, "urdf", "rob_accueil.urdf.xacro"]), " ",
        "use_mock_hardware:=", use_mock_hardware,
    ])
    # value_type=str : sinon le controller_manager tente de lire l'URDF comme du YAML.
    robot_description = {"robot_description": ParameterValue(robot_description_content, value_type=str)}
    controllers_file = PathJoinSubstitution([pkg, "config", "rob_accueil_controllers.yaml"])

    # controller_manager : charge l'URDF et le fichier de controllers.
    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[robot_description, controllers_file],
        output="both",
    )
    # Publie les TF a partir de l'URDF et des joint_states.
    robot_state_pub_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[robot_description],
    )
    # Toujours actif : expose le feedback des roues sur /joint_states.
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
    )
    # Phase 2 uniquement : le controller de base, demarre apres le broadcaster.
    base_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["diff_drive_base_controller", "--controller-manager", "/controller_manager"],
    )
    delay_base_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[base_controller_spawner],
        ),
        condition=IfCondition(start_base_controller),
    )

    return LaunchDescription(declared_arguments + [
        control_node,
        robot_state_pub_node,
        joint_state_broadcaster_spawner,
        delay_base_controller,
    ])
