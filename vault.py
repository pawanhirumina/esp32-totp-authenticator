import serial
import time
import tkinter as tk

PORT = "/dev/ttyACM0"
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(1.5)
ser.reset_input_buffer()

labels = {} # store widgets

def sync_time():
    unix = int(time.time())
    ser.write(f"TIME:{unix}\n".encode())
    ser.readline()

def fetch_and_show():
    try:
        ser.reset_input_buffer()
        ser.write(b"GET\n")

        codes = []
        start = time.time()
        while time.time() - start < 1.5:
            line = ser.readline().decode(errors='ignore').strip()
            if line == "END": break
            if "|" in line:
                try:
                    name, code, rem = line.split("|")
                    codes.append((name, code, rem))
                except: pass

        for name, code, rem in codes:
            if name not in labels:
                # create once
                frame = tk.Frame(content_frame, bg="#222", padx=15, pady=12)
                frame.pack(fill="x", pady=6)

                l1 = tk.Label(frame, text=name.upper(), bg="#222", fg="#888", font=("Arial", 9, "bold"))
                l1.pack(anchor="w")
                l2 = tk.Label(frame, text=code, bg="#222", fg="white", font=("Courier", 28, "bold"))
                l2.pack(anchor="w")
                l3 = tk.Label(frame, text="", bg="#222", fg="#00ff88", font=("Arial", 9))
                l3.pack(anchor="w")

                labels[name] = (l2, l3)

            # update only text, no destroy = no flash
            l_code, l_rem = labels[name]
            l_code.config(text=code)
            color = "#00ff88" if int(rem) > 10 else "#ff4444"
            l_rem.config(text=f"expires in {rem}s", fg=color)

    except Exception as e:
        print(e)

    root.after(1000, fetch_and_show)

# --- GUI ---
root = tk.Tk()
root.title("ESP32-C3 Offline Vault")
root.geometry("360x500")
root.configure(bg="#111")
tk.Label(root, text="OFFLINE VAULT - C3", bg="#111", fg="white", font=("Arial", 16, "bold")).pack(pady=12)
content_frame = tk.Frame(root, bg="#111")
content_frame.pack(fill="both", expand=True, padx=10, pady=10)

sync_time()
fetch_and_show()
root.mainloop()
