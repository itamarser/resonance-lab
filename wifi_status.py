import machine
import network
import ntptime
import time

try:
    from wifi_config import WIFI_PASSWORD, WIFI_SSID
except ImportError:
    WIFI_SSID = ""
    WIFI_PASSWORD = ""


LED_PIN = 2
CONNECT_TIMEOUT_SECONDS = 20

led = machine.Pin(LED_PIN, machine.Pin.OUT)


def blink(count, delay=0.15):
    for _ in range(count):
        led.on()
        time.sleep(delay)
        led.off()
        time.sleep(delay)


def connect_wifi():
    if not WIFI_SSID:
        raise RuntimeError("Set WIFI_SSID and WIFI_PASSWORD in wifi_config.py")

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to Wi-Fi:", WIFI_SSID)
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        start = time.time()
        while not wlan.isconnected():
            blink(1, 0.08)
            if time.time() - start > CONNECT_TIMEOUT_SECONDS:
                raise RuntimeError("Wi-Fi connection timed out")
            time.sleep(0.5)

    print("Connected")
    print("Network config:", wlan.ifconfig())
    return wlan


def sync_time():
    print("Syncing time from the internet...")
    ntptime.settime()
    print("UTC time:", time.localtime())


def main():
    blink(2)
    wlan = connect_wifi()
    sync_time()

    while True:
        led.value(1)
        print("Online. IP:", wlan.ifconfig()[0], "UTC:", time.localtime())
        time.sleep(5)
        led.value(0)
        time.sleep(1)


main()
