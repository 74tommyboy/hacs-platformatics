from datetime import timedelta

DOMAIN = "platformatics"
SCAN_INTERVAL = timedelta(seconds=30)
PLATFORMS = ["light", "sensor"]

SENSOR_DEFINITIONS = [
    # (device_key, name, unit, device_class, state_class)
    ("temperature", "Temperature", "°C", "temperature", "measurement"),
    ("humidity", "Humidity", "%", "humidity", "measurement"),
    ("pm2_5", "PM2.5", "µg/m³", "pm25", "measurement"),
    ("pm10", "PM10", "µg/m³", "pm10", "measurement"),
    ("vocIndex", "VOC Index", None, "volatile_organic_compounds_parts", "measurement"),
    ("daylightLevel", "Daylight Level", "%", None, "measurement"),
]
