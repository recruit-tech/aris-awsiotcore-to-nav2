# Copyright (c) Recruit Co., Ltd.
# Refer to LICENSE file for the full copyright and license information

import argparse
import json
import sys
import time
import traceback

from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder
from nav2_msgs.action import NavigateToPose
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node


class Locomotion():

    result_execute = 0
    result_complete = 1
    result_wrong = 4
    result_error = 9
    pressed = 0

    def __init__(
            self, topic, publish_topic, endpoint, client_id,
            path_to_cert, path_to_key, path_to_root):

        event_loop_group = io.EventLoopGroup(1)
        host_resolver = io.DefaultHostResolver(event_loop_group)
        client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

        self.TOPIC = topic
        self.PUBLISH_TOPIC = publish_topic

        self.mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=endpoint,
            cert_filepath=path_to_cert,
            pri_key_filepath=path_to_key,
            client_bootstrap=client_bootstrap,
            ca_filepath=path_to_root,
            client_id=client_id,
            clean_session=False,
            keep_alive_secs=6
        )

    def locomotion(self):
        rclpy.init()

        # Subscribe to AWSIoTCore
        connect_future = self.mqtt_connection.connect()
        connect_future.result()
        subscribe_future, packet_id = self.mqtt_connection.subscribe(
            topic=self.TOPIC,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self.on_message_received
        )

        try:
            while True:
                time.sleep(0.01)

        except KeyboardInterrupt:
            print("Catch Ctrl-C.")
        finally:
            print("Unsubscribe and disconnect MQTT connections.")
            subscribe_result = subscribe_future.result()
            disconnect_future = self.mqtt_connection.disconnect()
            disconnect_future.result()
            sys.exit(0)

    def on_message_received(self, topic, payload, **kwargs):
        parsed_message = self._checkJsonFormat(payload.decode())
        print(parsed_message)

        if (parsed_message):
            print("is_locomotoin_call")
            result = self._navigation(parsed_message)

            if (self.PUBLISH_TOPIC):
                message = {"result": result}
                self.mqtt_connection.publish(
                    topic=self.PUBLISH_TOPIC,
                    payload=json.dumps(message),
                    qos=mqtt.QoS.AT_LEAST_ONCE
                )
            print(result)
        else:
            print("Error: Received message has no json format data.")

    def _navigation(self, message):
        try:
            client = SimpleActionClient()
            client.wait_for_server()
        except Exception as e:
            traceback.print_exc()
            print(e)
            return self.result_error

        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = 'map'
        goal.pose.pose.position.x = \
            message["pos_x"] if "pos_x" in message else 0.0
        goal.pose.pose.position.y = \
            message["pos_y"] if "pos_y" in message else 0.0
        goal.pose.pose.position.z = \
            message["pos_z"] if "pos_z" in message else 0.0
        goal.pose.pose.orientation.x = \
            message["orientation_x"] if "orientation_x" in message else 0.0
        goal.pose.pose.orientation.y = \
            message["orientation_y"] if "orientation_y" in message else 0.0
        goal.pose.pose.orientation.z = \
            message["orientation_z"] if "orientation_z" in message else 0.0
        goal.pose.pose.orientation.w = \
            message["orientation_w"] if "orientation_w" in message else 0.0
        print(f'goal position: '
              f'({message["pos_x"]}, {message["pos_y"]}, {message["pos_z"]})')
        print(f'goal orientation: '
              f'({message["orientation_x"]}, {message["orientation_y"]}, '
              f'({message["orientation_z"]}, {message["orientation_w"]})')

        try:
            client.send_goal(goal)
            return self.result_complete
        except Exception as e:
            traceback.print_exc()
            print(e)
            return self.result_error

    def _checkJsonFormat(self, json_str):
        try:
            json_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(e)
            return None
        return json_data


class SimpleActionClient(Node):
    def __init__(self):
        super().__init__('action_client_node')
        self._ac = ActionClient(self, NavigateToPose, 'NavigateToPose')

    def wait_for_server(self):
        self._ac.wait_for_server()

    def send_goal(self, goal):
        print("send_goal")
        send_goal_future = self._ac.send_goal_async(
            goal, feedback_callback=self.feedback_callback
        )
        send_goal_future.add_done_callback(self.goal_response_callback)
        print("arrived_goal")

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            print('Goal rejected :(')
            return

        print('Goal accepted :)')

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        print('Received feedback: {0}'.format(feedback.partial_sequence))


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Receive positional information "
                    "from AWS IoT Core and send it to Navigation2"
    )
    parser.add_argument(
        "--topic-name", "-t", dest="topic", required=True,
        help="(Required) MQTT Topic name of AWS IoT Core."
    )
    parser.add_argument(
        "--publish-topic-name", "-n", dest="publish_topic",
        help="(Optional) MQTT Topic name to publish the locomotion result"
    )
    parser.add_argument(
        "--endpoint", "-e", dest="endpoint", required=True,
        help="(Required) AWS IoT Core endpoint."
    )
    parser.add_argument(
        "--client-id", "-i", dest="client_id", required=True,
        help="(Required) Client ID."
    )
    parser.add_argument(
        "--cert-path", "-c", dest="cert", required=True,
        help="(Required) Full path to certificate PEM file. "
             "(YOUR_ID-certificate.pem.crt)"
    )
    parser.add_argument(
        "--private-cert-path", "-p", dest="private_cert", required=True,
        help="(Required) Full path to private key PEM file. "
             "(YOUR_ID-private.pem.key)"
    )
    parser.add_argument(
        "--root-cert-path", "-r", dest="root_path", required=True,
        help="(Required) Full path to Root CA file."
    )
    args = parser.parse_args()

    locomotoin = Locomotion(
                    topic=args.topic, publish_topic=args.publish_topic,
                    endpoint=args.endpoint, client_id=args.client_id,
                    path_to_cert=args.cert, path_to_key=args.private_cert,
                    path_to_root=args.root_path
    )
    locomotoin.locomotion()


if __name__ == '__main__':
    main()
