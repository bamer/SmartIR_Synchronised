"""Constants for the SmartIR integration."""

import logging

DOMAIN = "smartir"
VERSION = "1.18.1"

CONF_CONTROLLER_TYPE = "controller_type"
CONF_DEVICE_TYPE = "device_type"
CONF_NAME = "name"
CONF_UNIQUE_ID = "unique_id"
CONF_DEVICE_CODE = "device_code"
CONF_CONTROLLER_DATA = "controller_data"
CONF_DELAY = "delay"
CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_HUMIDITY_SENSOR = "humidity_sensor"
CONF_POWER_SENSOR = "power_sensor"
CONF_POWER_SENSOR_RESTORE_STATE = "power_sensor_restore_state"

CONTROLLER_TYPES = {
    "broadlink": "Broadlink",
    "xiaomi": "Xiaomi IR Remote (ChuangmiIr)",
    "lookin": "LOOK.in Remote",
    "esphome": "ESPHome User-defined service for remote transmitter",
    "mqtt": "MQTT Publish service",
}

DEVICE_TYPES = {
    "climate": "Climate (Air Conditioner)",
    "fan": "Fan",
    "media_player": "Media Player (TV/Audio)",
    "light": "Light",
}

_LOGGER = logging.getLogger(__name__)
