#include <Arduino.h>
#include <TOTP.h>
#include <Preferences.h>
#include <ctype.h>
#include <string.h>

Preferences prefs;

const int LED_PIN = 8;

long timeOffset = 0;
bool timeSynced = false;

#define MAX_ACCOUNTS 10
#define MAX_NAME_LEN 32
#define MAX_SECRET_LEN 128

struct Account {
  char name[MAX_NAME_LEN];
  char secret[MAX_SECRET_LEN];
};

Account accounts[MAX_ACCOUNTS];
int accountCount = 0;
int base32_decode(const char* in, uint8_t* out) {
  const char* chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

  uint32_t buffer = 0;
  int bitsLeft = 0;
  int count = 0;

  for (int i = 0; in[i] && count < 32; i++) {
    char c = toupper(in[i]);

    if (c == '=' || c == ' ')
      continue;

    const char* p = strchr(chars, c);

    if (!p)
      continue;

    buffer = (buffer << 5) | (p - chars);
    bitsLeft += 5;

    if (bitsLeft >= 8) {
      out[count++] =
        (buffer >> (bitsLeft - 8)) & 0xFF;

      bitsLeft -= 8;
    }
  }

  return count;
}
long getNow() {
  return timeOffset + (millis() / 1000);
}
void saveAccounts() {
  prefs.begin("totp", false);

  prefs.putInt("count", accountCount);

  for (int i = 0; i < accountCount; i++) {
    char nameKey[16];
    char secretKey[16];

    snprintf(nameKey, sizeof(nameKey), "name%d", i);
    snprintf(secretKey, sizeof(secretKey), "secret%d", i);

    prefs.putString(nameKey, accounts[i].name);
    prefs.putString(secretKey, accounts[i].secret);
  }

  prefs.end();
}


void loadAccounts() {
  prefs.begin("totp", true);

  accountCount = prefs.getInt("count", 0);

  if (accountCount < 0 || accountCount > MAX_ACCOUNTS) {
    accountCount = 0;
  }

  for (int i = 0; i < accountCount; i++) {
    char nameKey[16];
    char secretKey[16];

    snprintf(nameKey, sizeof(nameKey), "name%d", i);
    snprintf(secretKey, sizeof(secretKey), "secret%d", i);

    String name = prefs.getString(nameKey, "");
    String secret = prefs.getString(secretKey, "");

    strncpy(
      accounts[i].name,
      name.c_str(),
      MAX_NAME_LEN - 1
    );

    accounts[i].name[MAX_NAME_LEN - 1] = '\0';

    strncpy(
      accounts[i].secret,
      secret.c_str(),
      MAX_SECRET_LEN - 1
    );

    accounts[i].secret[MAX_SECRET_LEN - 1] = '\0';
  }

  prefs.end();
}

void LedBlink() {
  for (int i = 0; i < 2; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(200);

    digitalWrite(LED_PIN, LOW);
    delay(200);
  }

  digitalWrite(LED_PIN, HIGH);
}
void addAccount(String data) {

  int separator = data.indexOf(':');

  if (separator <= 0) {
    Serial.println("ERR: Invalid ADD");
    return;
  }

  String name = data.substring(0, separator);
  String secret = data.substring(separator + 1);

  name.trim();
  secret.trim();
  secret.toUpperCase();
  secret.replace(" ", "");

  if (name.length() == 0 || secret.length() == 0) {
    Serial.println("ERR: Empty name or secret");
    return;
  }

  if (name.length() >= MAX_NAME_LEN) {
    Serial.println("ERR: Name too long");
    return;
  }

  if (secret.length() >= MAX_SECRET_LEN) {
    Serial.println("ERR: Secret too long");
    return;
  }

  // Check if account already exists
  for (int i = 0; i < accountCount; i++) {

    if (strcmp(accounts[i].name, name.c_str()) == 0) {

      strncpy(
        accounts[i].secret,
        secret.c_str(),
        MAX_SECRET_LEN - 1
      );

      accounts[i].secret[MAX_SECRET_LEN - 1] = '\0';

      saveAccounts();

      Serial.println("OK: Updated");
      return;
    }
  }

  if (accountCount >= MAX_ACCOUNTS) {
    Serial.println("ERR: Vault full");
    return;
  }

  strncpy(
    accounts[accountCount].name,
    name.c_str(),
    MAX_NAME_LEN - 1
  );

  accounts[accountCount].name[MAX_NAME_LEN - 1] = '\0';

  strncpy(
    accounts[accountCount].secret,
    secret.c_str(),
    MAX_SECRET_LEN - 1
  );

  accounts[accountCount].secret[MAX_SECRET_LEN - 1] = '\0';

  accountCount++;

  saveAccounts();

  Serial.println("OK: Added");
}
void deleteAccount(String name) {

  name.trim();

  for (int i = 0; i < accountCount; i++) {

    if (strcmp(accounts[i].name, name.c_str()) == 0) {

      for (int j = i; j < accountCount - 1; j++) {
        accounts[j] = accounts[j + 1];
      }

      accountCount--;

      memset(
        &accounts[accountCount],
        0,
        sizeof(Account)
      );

      saveAccounts();

      Serial.println("OK: Deleted");
      return;
    }
  }

  Serial.println("ERR: Account not found");
}

void listAccounts() {

  for (int i = 0; i < accountCount; i++) {
    Serial.println(accounts[i].name);
  }

  Serial.println("ENDLIST");
}



void clearAccounts() {

  prefs.begin("totp", false);
  prefs.clear();
  prefs.end();

  memset(
    accounts,
    0,
    sizeof(accounts)
  );

  accountCount = 0;

  Serial.println("OK: Cleared");
}



void sendCodes() {

  if (!timeSynced) {
    Serial.println("ERR: No time");
    return;
  }

  long now = getNow();

  for (int i = 0; i < accountCount; i++) {

    uint8_t hmacKey[32];

    int len = base32_decode(
      accounts[i].secret,
      hmacKey
    );

    if (len == 0)
      continue;

    TOTP totp(hmacKey, len);

    char* code = totp.getCode(now);

    int rem = 30 - (now % 30);

    Serial.printf(
      "%s|%s|%d\n",
      accounts[i].name,
      code,
      rem
    );
  }

  Serial.println("END");
}



void handleCommand(String line) {

  line.trim();


  if (line.startsWith("TIME:")) {

    long pc = line.substring(5).toInt();

    timeOffset =
      pc - (millis() / 1000);

    timeSynced = true;

    Serial.println("OK");

    return;
  }

 if (line.startsWith("ADD:")) {

    String data = line.substring(4);

    addAccount(data);

    return;
  }


 if (line.startsWith("DEL:")) {

    String name = line.substring(4);

    deleteAccount(name);

    return;
  }

  if (line == "LIST") {

    listAccounts();

    return;
  }

  if (line == "GET") {

    sendCodes();

    return;
  }

  if (line == "CLEAR") {

    clearAccounts();

    return;
  }


  Serial.println("ERR: Unknown command");
}


void setup() {

  pinMode(LED_PIN, OUTPUT);

  digitalWrite(LED_PIN, LOW);

  Serial.begin(115200);

  delay(1000);

  loadAccounts();

  Serial.println("READY");

  LedBlink();
}


void loop() {

  if (Serial.available()) {

    String line =
      Serial.readStringUntil('\n');

    handleCommand(line);
  }
}
