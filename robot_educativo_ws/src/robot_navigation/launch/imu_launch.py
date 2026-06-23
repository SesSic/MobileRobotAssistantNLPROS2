#!/usr/bin/env python3
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='robot_navigation',
            executable='imu_odometry_node',
            name='imu_odometry_node',
            parameters=[{
                'i2c_bus': 1,
                'device_address': 0x68,
                'publish_rate': 50,
                'calibration_time': 2.0,
                'frame_id': 'imu_link'
            }],
            output='screen'
        )
    ])