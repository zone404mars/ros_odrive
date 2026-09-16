# Teleop manette pour la base du robot d'accueil (DualShock 4 en Bluetooth).
# Demarre les deux noeuds de la chaine : joy lit le joystick et publie /joy,
# teleop_twist_joy convertit /joy en TwistStamped pour le diff_drive_controller.
# Les reglages (axes, echelles, zone morte) vivent dans config/rob_accueil_joy.yaml.
#
# Se lance separement du bringup de la base, qui doit tourner avec
# start_base_controller:=true pour que le controller ecoute les commandes.

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Arguments de lancement.
    declared_arguments = [
        DeclareLaunchArgument(
            "cmd_vel_topic",
            default_value="/diff_drive_base_controller/cmd_vel",
            description="Topic TwistStamped ecoute par le diff_drive_controller."),
    ]
    cmd_vel_topic = LaunchConfiguration("cmd_vel_topic")

    # Fichier de parametres commun aux deux noeuds. Il porte une section par nom
    # de noeud, d'ou les noms figes plus bas : les renommer rendrait le YAML muet.
    config_file = PathJoinSubstitution([
        FindPackageShare("odrive_rob_accueil"), "config", "rob_accueil_joy.yaml",
    ])

    # Driver joystick : lit /dev/input via SDL2, publie un sensor_msgs/Joy.
    joy_node = Node(
        package="joy",
        executable="joy_node",
        name="joy_node",
        parameters=[config_file],
        output="both",
    )
    # Convertisseur : /joy vers TwistStamped. Le remap est en forme relative,
    # pour rester correct si les noeuds sont un jour places dans un namespace.
    teleop_node = Node(
        package="teleop_twist_joy",
        executable="teleop_node",
        name="teleop_twist_joy_node",
        parameters=[config_file],
        remappings=[("cmd_vel", cmd_vel_topic)],
        output="both",
    )

    return LaunchDescription(declared_arguments + [joy_node, teleop_node])
