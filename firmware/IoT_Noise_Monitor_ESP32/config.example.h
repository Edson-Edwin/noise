#pragma once
// Copy to config.h. This file contains examples only; config.h is Git-ignored.
constexpr char WIFI_SSID[] = "YOUR_WIFI_NAME";
constexpr char WIFI_PASSWORD[] = "YOUR_WIFI_PASSWORD";
constexpr char API_URL[] = "https://YOUR-SERVICE.onrender.com/readings";
constexpr char DEVICE_API_KEY[] = "COPY_DEVICE_API_KEY_FROM_RENDER";
// Paste the issuing root CA certificate for your actual server (PEM).
// See docs/HARDWARE.md. Never replace verification with setInsecure().
constexpr char ROOT_CA[] = R"PEM(-----BEGIN CERTIFICATE-----
PASTE_YOUR_SERVER_ISSUING_ROOT_CA_HERE
-----END CERTIFICATE-----
)PEM";
constexpr int NOISE_THRESHOLD = 500;  // Starting point only; tune on your sensor.
constexpr int HYSTERESIS = 30;
constexpr bool BUZZER_ACTIVE_HIGH = true;
constexpr uint32_t SAMPLE_INTERVAL_MS = 2000;
