from machine import Pin, ADC
from time import sleep

soil = ADC(Pin(34))
soil.atten(ADC.ATTN_11DB)   # מאפשר קריאה בתחום גבוה יותר, מתאים ל-3.3V בערך
soil.width(ADC.WIDTH_12BIT) # ESP32: קריאה 0-4095

while True:
    value = soil.read()
    print("soil raw:", value)
    sleep(0.5)
