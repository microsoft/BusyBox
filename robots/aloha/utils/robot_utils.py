import time

import rclpy

from aloha.robot_utils import (
    get_arm_gripper_positions,
    move_arms,
    move_grippers,
    torque_off,
    torque_on,
)
from interbotix_xs_modules.xs_robot.arm import InterbotixManipulatorXS

# constants exist in the interbotics workspace install space
from aloha.real_env import (
    get_action,
    make_real_env
)
from aloha.constants import (
    DT,
    FOLLOWER_GRIPPER_JOINT_CLOSE,
    IS_MOBILE,
    LEADER_GRIPPER_CLOSE_THRESH,
    LEADER_GRIPPER_JOINT_MID,
    START_ARM_POSE,
)
from interbotix_common_modules.common_robot.robot import (
    create_interbotix_global_node,
    robot_shutdown,
    robot_startup,
)

def opening_ceremony(
    leader_bot_left: InterbotixManipulatorXS,
    leader_bot_right: InterbotixManipulatorXS,
    follower_bot_left: InterbotixManipulatorXS,
    follower_bot_right: InterbotixManipulatorXS,
    gravity_compensation: bool = False,
    initial_pose: list = None,
):
    """Move all 4 robots to a pose where it is easy to start demonstration."""
    # reboot gripper motors, and set operating modes for all motors
    follower_bot_left.core.robot_reboot_motors('single', 'gripper', True)
    follower_bot_left.core.robot_set_operating_modes('group', 'arm', 'position')
    follower_bot_left.core.robot_set_operating_modes('single', 'gripper', 'current_based_position')
    leader_bot_left.core.robot_set_operating_modes('group', 'arm', 'position')
    leader_bot_left.core.robot_set_operating_modes('single', 'gripper', 'position')
    follower_bot_left.core.robot_set_motor_registers('single', 'gripper', 'current_limit', 300)

    follower_bot_right.core.robot_reboot_motors('single', 'gripper', True)
    follower_bot_right.core.robot_set_operating_modes('group', 'arm', 'position')
    follower_bot_right.core.robot_set_operating_modes(
        'single', 'gripper', 'current_based_position'
    )
    leader_bot_right.core.robot_set_operating_modes('group', 'arm', 'position')
    leader_bot_right.core.robot_set_operating_modes('single', 'gripper', 'position')
    follower_bot_left.core.robot_set_motor_registers('single', 'gripper', 'current_limit', 300)

    torque_on(follower_bot_left)
    torque_on(leader_bot_left)
    torque_on(follower_bot_right)
    torque_on(leader_bot_right)

    # move arms to starting position
    if initial_pose is None:
        print('Moving arms to DEFAULT starting position')
        start_arm_qpos = START_ARM_POSE[:6]
        move_arms(
            [leader_bot_left, follower_bot_left, leader_bot_right, follower_bot_right],
            [start_arm_qpos] * 4,
            moving_time=1.5,
        )
    else:
        print('Moving arms to CUSTOM starting position')
        move_arms(
            [leader_bot_left, follower_bot_left, leader_bot_right, follower_bot_right],
            initial_pose,
            moving_time=1.5,
        )
    # move grippers to starting position
    move_grippers(
        [leader_bot_left, follower_bot_left, leader_bot_right, follower_bot_right],
        [LEADER_GRIPPER_JOINT_MID, FOLLOWER_GRIPPER_JOINT_CLOSE] * 2,
        moving_time=0.5,
    )

    # press gripper to start data collection
    # disable torque for only gripper joint of leader robot to allow user movement
    leader_bot_left.core.robot_torque_enable('single', 'gripper', False)
    leader_bot_right.core.robot_torque_enable('single', 'gripper', False)
    print('Close the gripper to start')
    pressed = False
    while rclpy.ok() and not pressed:
        gripper_pos_left = get_arm_gripper_positions(leader_bot_left)
        gripper_pos_right = get_arm_gripper_positions(leader_bot_right)
        pressed = (
            (gripper_pos_left < LEADER_GRIPPER_CLOSE_THRESH) and
            (gripper_pos_right < LEADER_GRIPPER_CLOSE_THRESH)
        )
        time.sleep(DT/10)
    torque_off(leader_bot_left)
    torque_off(leader_bot_right)
    print('Robot has been started')


def bringup_robots():
    node = create_interbotix_global_node('aloha')

    # source of data
    leader_bot_left = InterbotixManipulatorXS(
        robot_model='wx250s',
        robot_name='leader_left',
        node=node,
        iterative_update_fk=False,
    )
    leader_bot_right = InterbotixManipulatorXS(
        robot_model='wx250s',
        robot_name='leader_right',
        node=node,
        iterative_update_fk=False,
    )

    env = make_real_env(
        node=node,
        setup_robots=False,
        setup_base=IS_MOBILE,
        torque_base=False,
    )

    robot_startup(node)

    return node, leader_bot_left, leader_bot_right, env
