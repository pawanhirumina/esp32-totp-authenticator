#!/usr/bin/env python3
import serial, time, sys, argparse, re, getpass
from serial.tools import list_ports
from urllib.parse import urlparse, parse_qs, unquote
from colorama import init, Fore, Style
init(autoreset=True)

BASE32_RE = re.compile(r'^[A-Z2-7]+=*$')

def find_port():
    for p in list_ports.comports():
        if "ACM" in p.device or "USB" in p.device: return p.device
    return "/dev/ttyACM0"

def connect():
    port=find_port()
    try:
        ser=serial.Serial(port,115200,timeout=1)
        time.sleep(1.2); ser.reset_input_buffer()
        ser.write(f"TIME:{int(time.time())}\n".encode()); time.sleep(0.2); ser.readline()
        return ser, port
    except Exception as e:
        print(f"{Fore.RED}[!]{Style.RESET_ALL} Can't open {port}: {e}"); sys.exit(1)

def parse_otpauth(uri):
    try:
        p = urlparse(uri)
    except Exception:
        return None
    if p.scheme.lower() != "otpauth": return None
    try:
        secret = (parse_qs(p.query).get("secret") or [None])[0]
    except Exception:
        secret = None
    if not secret: return None
    secret = unquote(str(secret))
    path = unquote(p.path.lstrip("/"))
    name = path.split(":")[0] if path else ""
    if not name:
        name = (parse_qs(p.query).get("issuer") or [""])[0]
    return name, secret

def detect_type(secret, forced=None):
    if forced in ("totp", "pass"): return forced
    if secret and BASE32_RE.match(secret) and len(secret) >= 8: return "totp"
    return "pass"

def send_add(ser, name, secret, ttype):
    ser.write(f"ADD:{name}:{secret}:{ttype}\n".encode())
    return ser.readline().decode().strip()

def cmd_list():
    ser,port=connect(); ser.write(b"LIST\n")
    print(f"\n{Style.BRIGHT}Vault on {port}:{Style.RESET_ALL}\n{Fore.LIGHTBLACK_EX}{'-'*30}{Style.RESET_ALL}")
    start=time.time(); found=False
    while time.time()-start<2:
        line=ser.readline().decode(errors='ignore').strip()
        if line=="ENDLIST": break
        if line and ":" not in line and "|" not in line and "READY" not in line and "OK" not in line and line!="":
            if "ERR" not in line:
                print(f" {Fore.CYAN}•{Style.RESET_ALL} {line}"); found=True
            else:
                print(f" {Fore.RED}{line}{Style.RESET_ALL}")
    if not found: print(f" {Fore.LIGHTBLACK_EX}(empty){Style.RESET_ALL}")
    ser.close()

def cmd_add(name, secret, ftype):
    if secret == "-": secret = getpass.getpass("Password: ")
    parsed = parse_otpauth(secret)
    if parsed:
        uri_name, secret = parsed
        if not name: name = uri_name
    if not name or not secret:
        print(f"{Fore.RED}[!]{Style.RESET_ALL} Usage: pyauth add NAME SECRET"); sys.exit(1)
    ttype = detect_type(secret, ftype)
    if ttype == "totp": secret = secret.upper().strip().replace(" ", "")
    ser, port = connect()
    res = send_add(ser, name, secret, ttype)
    col = Fore.GREEN if "OK" in res else Fore.RED
    print(f"{Fore.LIGHTBLACK_EX}[{ttype}]{Style.RESET_ALL} {Style.BRIGHT}{name}{Style.RESET_ALL} -> {col}{res}{Style.RESET_ALL}")
    ser.close()

def cmd_bulk(path, ftype):
    try:
        with open(path) as f: lines = f.readlines()
    except OSError as e:
        print(f"{Fore.RED}[!]{Style.RESET_ALL} Can't read {path}: {e}"); sys.exit(1)
    ser, port = connect()
    for lineno, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"): continue
        name, secret = None, None
        if line.startswith("otpauth://"):
            parsed = parse_otpauth(line)
            if not parsed:
                print(f"{Fore.RED}{path}:{lineno}: ERR bad otpauth URI{Style.RESET_ALL}"); continue
            name, secret = parsed
        elif ":" in line:
            name, secret = line.split(":", 1); name, secret = name.strip(), secret.strip()
        else:
            parts = line.split(None, 1)
            if len(parts) < 2:
                print(f"{Fore.RED}{path}:{lineno}: ERR expected NAME SECRET{Style.RESET_ALL}"); continue
            name, secret = parts[0], parts[1]
        if not name or not secret: continue
        ttype = detect_type(secret, ftype)
        if ttype == "totp": secret = secret.upper().strip().replace(" ", "")
        res = send_add(ser, name, secret, ttype)
        col = Fore.GREEN if "OK" in res else Fore.RED
        print(f"{name} {Fore.LIGHTBLACK_EX}[{ttype}]{Style.RESET_ALL} -> {col}{res}{Style.RESET_ALL}")
    ser.close()

def cmd_remove(name):
    ser,port=connect(); ser.write(f"DEL:{name}\n".encode())
    res = ser.readline().decode().strip()
    col = Fore.GREEN if "OK" in res else Fore.RED
    print(f"{col}{res}{Style.RESET_ALL}"); ser.close()

def cmd_codes():
    ser, port = connect()
    print(f"\n{Style.BRIGHT}Codes from {port}{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}(Ctrl+C to exit){Style.RESET_ALL}\n")
    prev_lines = 0
    try:
        while True:
            ser.write(b"GET\n")
            start = time.time()
            lines = []
            while time.time() - start < 1.5:
                l = ser.readline().decode(errors='ignore').strip()
                if l == "END": break
                if "|" in l: lines.append(l)

            if prev_lines > 0:
                sys.stdout.write(f"\033[{prev_lines}F")

            for item in lines:
                try:
                    n, c, r = item.split("|")
                    if r.isdigit():
                        timer_color = Fore.GREEN if int(r) > 10 else Fore.RED
                        # FIXED: now actually using timer_color
                        sys.stdout.write(f"\033[K{Fore.LIGHTBLACK_EX}{n:20}{Style.RESET_ALL} {Style.BRIGHT}{Fore.WHITE}{c}{Style.RESET_ALL} {timer_color}({r}s){Style.RESET_ALL}\n")
                    else:
                        sys.stdout.write(f"\033[K{Fore.LIGHTBLACK_EX}{n:20}{Style.RESET_ALL} {Style.BRIGHT}{Fore.WHITE}{c}{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}(stored){Style.RESET_ALL}\n")
                except: pass

            sys.stdout.write(f"\033[K{Fore.LIGHTBLACK_EX}{'-'*30}{Style.RESET_ALL}\n")
            sys.stdout.flush()
            prev_lines = len(lines) + 1
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n")
    ser.close()

def cmd_show():
    import tkinter as tk
    ser,port=connect(); ser.reset_input_buffer(); labels={}
    root=tk.Tk(); root.title(f"Vault {port}"); root.geometry("380x550"); root.configure(bg="#111")
    tk.Label(root,text=f"OFFLINE VAULT {port}",bg="#111",fg="white",font=("Arial",12,"bold")).pack(pady=12)
    content=tk.Frame(root,bg="#111"); content.pack(fill="both",expand=True,padx=10,pady=10)
    def fetch():
        try:
            ser.write(b"GET\n"); codes=[]; start=time.time()
            while time.time()-start<1.5:
                l=ser.readline().decode(errors='ignore').strip()
                if l=="END": break
                if "|" in l:
                    try: codes.append(l.split("|"))
                    except: pass
            for n,c,r in codes:
                if n not in labels:
                    f=tk.Frame(content,bg="#222",padx=15,pady=12); f.pack(fill="x",pady=6)
                    tk.Label(f,text=n.upper(),bg="#222",fg="#888",font=("Arial",9,"bold")).pack(anchor="w")
                    l2=tk.Label(f,text=c,bg="#222",fg="white",font=("Courier",28,"bold")); l2.pack(anchor="w")
                    l3=tk.Label(f,bg="#222",font=("Arial",9)); l3.pack(anchor="w")
                    labels[n]=(l2,l3)
                l2,l3=labels[n]; l2.config(text=c); l3.config(text=f"expires in {r}s" if r.isdigit() else "stored password", fg="#00ff88" if (r.isdigit() and int(r)>10) else "#ff4444")
        except Exception as e: print(e)
        root.after(1000,fetch)
    fetch(); root.mainloop()

parser=argparse.ArgumentParser(prog="pyauth")
sub=parser.add_subparsers(dest="cmd")
sub.add_parser("list")
a=sub.add_parser("add"); a.add_argument("name"); a.add_argument("secret"); a.add_argument("-t","--type",choices=["totp","pass"],default=None)
r=sub.add_parser("remove"); r.add_argument("name")
b=sub.add_parser("bulk"); b.add_argument("file"); b.add_argument("-t","--type",choices=["totp","pass"],default=None)
sub.add_parser("codes"); sub.add_parser("show"); sub.add_parser("clear")
args=parser.parse_args()
if not args.cmd or args.cmd=="show": cmd_show()
elif args.cmd=="list": cmd_list()
elif args.cmd=="add": cmd_add(args.name, args.secret, args.type)
elif args.cmd=="remove": cmd_remove(args.name)
elif args.cmd=="bulk": cmd_bulk(args.file, args.type)
elif args.cmd=="codes": cmd_codes()
elif args.cmd=="clear":
    ser,port=connect(); ser.write(b"CLEAR\n"); print(f"{Fore.YELLOW}{ser.readline().decode().strip()}{Style.RESET_ALL}"); ser.close()