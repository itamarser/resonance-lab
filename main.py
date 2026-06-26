import machine
import network
import socket
import time

try:
    import urequests as requests
except ImportError:
    requests = None

try:
    import ntptime
except ImportError:
    ntptime = None

try:
    from wifi_config import WIFI_PASSWORD, WIFI_SSID
except ImportError:
    WIFI_SSID = ""
    WIFI_PASSWORD = ""

try:
    from thingspeak_config import THINGSPEAK_WRITE_API_KEY
except ImportError:
    THINGSPEAK_WRITE_API_KEY = ""

soil = machine.ADC(machine.Pin(34))
soil.atten(machine.ADC.ATTN_11DB)
soil.width(machine.ADC.WIDTH_12BIT)

DRY = 2800
WET = 1300
LED_PIN = 2
CONNECT_TIMEOUT_SECONDS = 45
SLEEP_SECONDS = 30 * 60
APP_VERSION = "soil-monitor-deepsleep-30min-v2"

led = machine.Pin(LED_PIN, machine.Pin.OUT)


def blink(count, delay=0.15):
    for _ in range(count):
        led.on()
        time.sleep(delay)
        led.off()
        time.sleep(delay)


def moisture_percent(raw):
    percent = (DRY - raw) * 100 / (DRY - WET)

    if percent < 0:
        percent = 0
    if percent > 100:
        percent = 100

    return percent


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
    if ntptime is None:
        return

    try:
        print("Syncing time from the internet...")
        ntptime.settime()
        print("UTC time:", time.localtime())
    except Exception as err:
        print("Time sync failed:", err)


def send_to_thingspeak(raw, moisture):
    if not THINGSPEAK_WRITE_API_KEY:
        raise RuntimeError("Set THINGSPEAK_WRITE_API_KEY in thingspeak_config.py")

    url = (
        "http://api.thingspeak.com/update"
        "?api_key={}&field1={}&field2={:.1f}".format(
            THINGSPEAK_WRITE_API_KEY,
            raw,
            moisture,
        )
    )

    response = None
    if requests is not None:
        try:
            response = requests.get(url)
            entry_id = response.text.strip()
        finally:
            if response is not None:
                response.close()
    else:
        entry_id = send_http_get_without_requests(
            "api.thingspeak.com",
            "/update?api_key={}&field1={}&field2={:.1f}".format(
                THINGSPEAK_WRITE_API_KEY,
                raw,
                moisture,
            ),
        )

    if entry_id == "0":
        print("ThingSpeak rejected update, probably rate limit")
    else:
        print("ThingSpeak entry:", entry_id)


def send_http_get_without_requests(host, path):
    addr = socket.getaddrinfo(host, 80)[0][-1]
    sock = socket.socket()

    try:
        sock.connect(addr)
        request = (
            "GET {} HTTP/1.0\r\n"
            "Host: {}\r\n"
            "Connection: close\r\n\r\n"
        ).format(path, host)
        sock.send(request.encode())

        response = b""
        while True:
            chunk = sock.recv(512)
            if not chunk:
                break
            response += chunk

        body = response.split(b"\r\n\r\n", 1)[-1]
        return body.decode().strip()
    finally:
        sock.close()


def go_to_sleep(wlan=None):
    led.off()
    if wlan is not None:
        wlan.active(False)

    print("Going to deep sleep for", SLEEP_SECONDS, "seconds")
    machine.deepsleep(SLEEP_SECONDS * 1000)


def main():
    print("Starting", APP_VERSION)
    blink(2)
    wlan = None

    try:
        wlan = connect_wifi()
    except Exception as err:
        print("Wi-Fi failed:", err)
        go_to_sleep(wlan)

    sync_time()

    raw = soil.read()
    moisture = moisture_percent(raw)
    print("raw:", raw, "moisture:", round(moisture, 1), "%")

    try:
        led.on()
        send_to_thingspeak(raw, moisture)
    except Exception as err:
        print("Upload failed:", err)
    finally:
        go_to_sleep(wlan)


main()
