import sys
from os.path import exists
import paho.mqtt.client as mqtt
from time import sleep
from random import uniform
from configparser import ConfigParser

DEFAULT_PATH = 'config.ini'
SECS_PER_MOUTH = 2592000
WAITING_CONFIG = 3


def greetings():
    return "    ________          __       _                        __\n" \
           "   / ____/ /__  _____/ /______(_)____   ____ ___  ___  / /____  _____\n" \
           "  / __/ / / _ \/ ___/ __/ ___/ / ___/  / __ `__ \/ _ \/ __/ _ \/ ___/\n" \
           " / /___/ /  __/ /__/ /_/ /  / / /__   / / / / / /  __/ /_/  __/ /\n" \
           "/_____/_/\___/\___/\__/_/  /_/\___/  /_/ /_/ /_/\___/\__/\___/_/\n" \
           "\n" \
           "Welcome to Electric Meter v.0.1\n"


def on_connect(client, userdata, flags, rc):
    print('Connected with result code ' + str(rc))


def on_disconnect():
    print('Disconnected')


def on_message(client, userdata, msg):
    print(msg.topic+' '+str(msg.payload))


# publish message to MQTT
def publish(type_of_value, data):
    topic = '/'.join((sys_cfg['id'], type_of_value))
    value = f'{data:.{5}f}'
    mqttc.publish(topic, value)


# storing values
def storing(name='storage', *args):
    store_data = b''

    if exists(name):
        with open(name, 'rb') as storage:
            store_data = storage.readline()

    if not store_data:
        values = args
    else:
        floated_data = tuple(float(v) for v in store_data.split())
        values = list(map(lambda arg, data: data+arg, args, floated_data))

    store_data = ' '.join(str(val) for val in values).encode()

    with open(name, 'wb+') as storage:
        storage.write(store_data)

    return store_data


# parsing config section to dictionary
def sect_to_dict(section):
    def to_int(val):
        try:
            if '.' in val[1]:
                return val[0], float(val[1])
            return val[0], int(val[1])
        except ValueError:
            return val

    return dict(map(to_int, section.items()))


# eject configuration and creating mqtt client
def setup(path_to_cfg=DEFAULT_PATH):
    cfg = ConfigParser()
    while not cfg.read(path_to_cfg):
        print('Waiting configuration')
        sleep(WAITING_CONFIG)

    # create MQTT client
    mqttc = None
    if 'MQTT' in cfg.keys():
        mqttc = mqtt.Client()
        mqttc.on_connect = on_connect
        mqttc.on_disconnect = on_disconnect
        mqttc.on_message = on_message
        mqtt_cfg = sect_to_dict(cfg["MQTT"])
        print(f'Connecting to {mqtt_cfg["host"]}:{mqtt_cfg["port"]}')
        try:
            mqttc.connect(**mqtt_cfg)
        except OSError as e:
            print(e)

    return sect_to_dict(cfg['SYSTEM']), sect_to_dict(cfg['ELECTRICITY']), mqttc


# main logic
def loop():
    consumption = cons + uniform(-cons, cons) / 2
    total_cost = consumption * electricity['cost']

    storing('storage', consumption, total_cost)

    if mqttc and mqttc.is_connected():
        publish('consumption', consumption)
        publish('cost', total_cost)


if __name__ == '__main__':
    # greetings message
    print(greetings())

    path = DEFAULT_PATH
    if len(sys.argv) > 1:
        path = sys.argv[1]

    sys_cfg, electricity, mqttc = setup(path)

    # consumption per seconds
    cons = electricity['avrg_cons'] / SECS_PER_MOUTH * sys_cfg["interval"]

    if mqttc:
        mqttc.loop_start()

    while True:
        loop()
        sleep(sys_cfg["interval"])
