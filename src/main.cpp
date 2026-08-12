#include <Arduino.h>
#include <TOTP.h>

struct Account {
  const char* name;
  const char* secret;
};

Account accounts[] = {
  {"Shop2Topup", "YOUR SECRET HERE"},
  {"GitHub", "YOUR SECRET HERE"},
  {"Google", "YOUR SECRET HERE"}
};

long timeOffset = 0;
bool timeSynced = false;
uint8_t hmacKey[32];

int base32_decode(const char* in, uint8_t* out) {
  const char* chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  int buffer = 0, bitsLeft = 0, count = 0;
  for (int i = 0; in[i]; i++) {
    char c = toupper(in[i]);
    if (c == '=' || c == ' ') continue;
    const char* p = strchr(chars, c);
    if (!p) continue;
    buffer = (buffer << 5) | (p - chars);
    bitsLeft += 5;
    if (bitsLeft >= 8) {
      out[count++] = (buffer >> (bitsLeft - 8)) & 0xFF;
      bitsLeft -= 8;
    }
  }
  return count;
}

long getNow() {
  return timeOffset + (millis() / 1000);
}

void sendCodes() {
  if (!timeSynced) {
    Serial.println("ERR: No time");
    return;
  }
  long now = getNow();
  for (auto acc : accounts) {
    int len = base32_decode(acc.secret, hmacKey);
    if(len==0) continue;
    TOTP totp = TOTP(hmacKey, len);
    char* code = totp.getCode(now);
    int rem = 30 - (now % 30);
    Serial.printf("%s|%s|%d\n", acc.name, code, rem);
  }
  Serial.println("END");
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("READY");
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.startsWith("TIME:")) {
      long pc = line.substring(5).toInt();
      timeOffset = pc - (millis() / 1000);
      timeSynced = true;
      Serial.println("OK");
    }
    if (line == "GET") sendCodes();
  }
}
