#!/usr/bin/env python3
# Teleop clavier aux fleches pour la base du robot d'accueil.
# Tenir une fleche fait monter la vitesse dans cette direction ; relacher la
# fait redescendre doucement vers zero. Publie un TwistStamped sur
# /diff_drive_base_controller/cmd_vel (type attendu par diff_drive_controller 4.x).
#
# Limite terminal : stdin ne donne pas d'evenement "touche relachee". On se base
# sur l'auto-repeat : tant qu'une fleche est tenue, des evenements arrivent ;
# passe hold_timeout sans evenement, la touche est consideree relachee.

import sys
import select
import termios
import tty
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped

# Sequences d'echappement des fleches (ESC [ A/B/C/D).
KEY_UP = "\x1b[A"
KEY_DOWN = "\x1b[B"
KEY_RIGHT = "\x1b[C"
KEY_LEFT = "\x1b[D"


class ArrowTeleop(Node):
    # Noeud teleop clavier : rampe a la tenue, decroissance au relachement.

    def __init__(self):
        super().__init__("arrow_teleop")
        self._init_params()
        self._init_state()
        self._init_io()

    def _init_params(self):
        # Declare et lit les parametres reglables (valeurs de depart prudentes).
        self.declare_parameter("topic", "/diff_drive_base_controller/cmd_vel")
        self.declare_parameter("max_linear", 0.3)     # m/s
        self.declare_parameter("max_angular", 0.8)    # rad/s
        self.declare_parameter("linear_step", 0.1)    # hausse par tick tenu (regle pour 10 Hz)
        self.declare_parameter("angular_step", 0.25)
        self.declare_parameter("decay", 0.77)         # facteur de decroissance par tick relache (10 Hz)
        self.declare_parameter("rate", 10.0)          # Hz - cadence de publication du Twist
        self.declare_parameter("hold_timeout", 0.30)  # s sans evenement = touche relachee
        self.max_linear = self.get_parameter("max_linear").value
        self.max_angular = self.get_parameter("max_angular").value
        self.linear_step = self.get_parameter("linear_step").value
        self.angular_step = self.get_parameter("angular_step").value
        self.decay = self.get_parameter("decay").value
        self.hold_timeout = self.get_parameter("hold_timeout").value

    def _init_state(self):
        # Vitesses courantes et date de derniere vue de chaque direction.
        self.linear = 0.0
        self.angular = 0.0
        self.last_seen = {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}

    def _init_io(self):
        # Publisher, terminal en mode brut non bloquant, timer de boucle.
        topic = self.get_parameter("topic").value
        rate = self.get_parameter("rate").value
        self.pub = self.create_publisher(TwistStamped, topic, 10)
        self.fd = sys.stdin.fileno()
        self.old_term = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)
        self.timer = self.create_timer(1.0 / rate, self.on_tick)
        self.get_logger().info(
            "Fleches pour piloter, tenir pour accelerer, relacher pour ralentir. 'q' pour quitter."
        )

    def read_keys(self):
        # Vide stdin ; met a jour last_seen selon les fleches lues. Renvoie "quit" si 'q'.
        now = time.monotonic()
        data = ""
        while select.select([sys.stdin], [], [], 0)[0]:
            data += sys.stdin.read(1)
        if "q" in data:
            return "quit"
        for seq, name in ((KEY_UP, "up"), (KEY_DOWN, "down"),
                          (KEY_LEFT, "left"), (KEY_RIGHT, "right")):
            if seq in data:
                self.last_seen[name] = now
        return None

    def held(self, key, now):
        # Vrai si la touche a ete vue dans la derniere fenetre hold_timeout.
        return (now - self.last_seen[key]) < self.hold_timeout

    def ramp(self, value, up, down, step, limit, now):
        # Monte vers +/-limit si tenu, sinon decroit vers zero.
        if self.held(up, now):
            return min(value + step, limit)
        if self.held(down, now):
            return max(value - step, -limit)
        value *= self.decay
        return 0.0 if abs(value) < 1e-3 else value

    def on_tick(self):
        # Une iteration : lit le clavier, met a jour les vitesses, publie.
        if self.read_keys() == "quit":
            self.stop_and_quit()
            return
        now = time.monotonic()
        self.linear = self.ramp(self.linear, "up", "down",
                                self.linear_step, self.max_linear, now)
        self.angular = self.ramp(self.angular, "left", "right",
                                 self.angular_step, self.max_angular, now)
        self.publish()

    def publish(self):
        # Publie l'etat courant en TwistStamped horodate.
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.twist.linear.x = self.linear
        msg.twist.angular.z = self.angular
        self.pub.publish(msg)

    def stop_and_quit(self):
        # Publie un arret, restaure le terminal, coupe le noeud.
        self.linear = 0.0
        self.angular = 0.0
        self.publish()
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_term)
        self.get_logger().info("Arret teleop.")
        rclpy.shutdown()


def main():
    rclpy.init()
    node = ArrowTeleop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(node.fd, termios.TCSADRAIN, node.old_term)
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
