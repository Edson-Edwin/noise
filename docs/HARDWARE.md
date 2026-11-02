# ESP32 setup and verification

The sketch supplied here is new code based on your handover. Physical board selection, upload, wiring, network behavior and sensor calibration must be checked on your Mac and ESP32.

## 1. Select the board in Arduino IDE

1. Open `firmware/IoT_Noise_Monitor_ESP32/IoT_Noise_Monitor_ESP32.ino`.
2. In **Select Other Board and Port**, search for **ESP32 Dev Module**.
3. Select that board. Choose the connected USB serial port. Your handover recorded `/dev/cu.usbserial-0001`; recheck it rather than assuming it is unchanged.
4. Click **OK**. ESP32 Arduino Core **3.3.12** is the target from the handover.

The board selection window has no API URL field. The API URL belongs in `config.h` beside the sketch.

## 2. Create the private configuration

Duplicate `config.example.h` in the same sketch folder and name the copy `config.h`. Edit the copy in Arduino IDE or a text editor:

- Set your current Wi-Fi SSID and password. Do not reuse the old handover values without checking them.
- Set the actual Render HTTPS `/readings` URL after deployment.
- Set the `DEVICE_API_KEY` from Render, not the dashboard key.
- Set `ROOT_CA` to the issuing **root CA** certificate in PEM format for the actual HTTPS service.
- Start with the example threshold, then tune it using Serial Monitor.

To obtain the public root certificate, open the deployed HTTPS site in your browser, inspect its certificate chain, select the root certificate and export it as Base-64/PEM (including `BEGIN CERTIFICATE` and `END CERTIFICATE`). Verify its fingerprint against the certificate authority's official site. Browser export labels differ; do not paste a binary DER file or the short-lived leaf certificate. If the server later changes certificate authorities, update and reflash the trust anchor. The sketch uses NTP and CA validation; it never uses `setInsecure()`.

For the first local hardware check, example HTTPS values can remain placeholders. The upload will fail until configured, but local sampling and LEDs still run. Do not mistake this for a passed cloud integration test.

## 3. Verify, upload and open Serial Monitor

1. Click **Verify (✓)**. Fix compilation errors before upload.
2. Connect the ESP32 with a USB data cable and click **Upload (→)**.
3. If it stalls at **Connecting**, hold **BOOT** until uploading begins, then release.
4. Open **Tools → Serial Monitor** and select **115200 baud**.
5. Confirm repeated `score=… noisy=…` output. After cloud setup, confirm HTTP `201` or `200` too.

## 4. Wire hardware with USB power disconnected

| Component | Connection |
| --- | --- |
| KY-038 VCC | ESP32 3.3V |
| KY-038 GND | ESP32 GND |
| KY-038 AO | GPIO 34 |
| KY-038 DO | Optional GPIO 27; this sketch does not use it |
| Green LED anode | GPIO 18 through 220Ω resistor |
| Red LED anode | GPIO 19 through 220Ω resistor |
| Both LED cathodes | GND |
| Buzzer signal | GPIO 23 |
| Buzzer ground | GND |

Use a buzzer module with a compatible logic input. Check its supply voltage and current. A bare/high-current buzzer needs a suitable transistor driver and appropriate protection; do not power it directly from the GPIO. This sketch uses an on/off **active buzzer**. A passive buzzer needs PWM code. Change `BUZZER_ACTIVE_HIGH` if the module's logic is inverted.

## 5. Tune and check

1. Observe the relative score in a quiet room, then during normal talking and a clap.
2. Set `NOISE_THRESHOLD` above ordinary background readings and below the signal you want to flag.
3. Keep `HYSTERESIS` positive and smaller than the threshold to reduce rapid switching near the boundary.
4. Re-upload and check green = normal, red + buzzer = noisy.
5. Confirm the buzzer itself does not repeatedly trigger the microphone. Separate the sensor from the buzzer or disable/mute the buzzer if acoustic feedback persists.
6. Turn off Wi-Fi temporarily. The LEDs/buzzer should continue responding, and uploads should resume after reconnection.

The loop samples 400 analog readings, computes maximum minus minimum and repeats about every two seconds. GPIO34 is an ADC1 input, suitable alongside Wi-Fi. The score is not calibrated SPL and must never be labeled accurate decibels.

The network task has a 30-reading RAM queue. It drops old queued readings when full, discards pending readings older than two minutes and loses queued data on power loss. This is a low-budget monitor, not a lossless logger. The database records **receipt time**, not precise measurement time; retries can arrive late. Each reading has a stable UUID so a lost HTTP response does not create duplicates.

Reference: [Espressif secure client documentation](https://github.com/espressif/arduino-esp32/blob/master/libraries/NetworkClientSecure/README.md).
