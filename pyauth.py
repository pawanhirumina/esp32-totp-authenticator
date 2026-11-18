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

# ---------- FULLSCREEN CODES UI (curses) ----------
def cmd_codes():
    import curses
    ser, port = connect()
    try:
        curses.wrapper(_codes_ui, ser, port)
    except KeyboardInterrupt:
        pass
    finally:
        try: ser.close()
        except: pass

def _codes_ui(stdscr, ser, port):
    import curses
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(200)
    curses.use_default_colors()
    try: curses.start_color()
    except: pass
    curses.init_pair(1, curses.COLOR_WHITE, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_RED, -1)
    curses.init_pair(4, curses.COLOR_CYAN, -1)
    curses.init_pair(5, curses.COLOR_YELLOW, -1)

    codes = []
    last_fetch = 0
    status = "connecting..."

    while True:
        key = stdscr.getch()
        if key in (ord('q'), ord('Q'), 27):
            break
        if key == curses.KEY_RESIZE:
            pass

        now = time.time()
        if now - last_fetch >= 1.0:
            last_fetch = now
            try:
                ser.reset_input_buffer()
                ser.write(b"GET\n")
                lines = []
                start = time.time()
                while time.time() - start < 1.0:
                    try:
                        l = ser.readline().decode(errors='ignore').strip()
                    except Exception:
                        # device dropped mid-read - try to reconnect
                        status = "RECONNECTING..."
                        try: ser.close()
                        except: pass
                        import serial as _serial
                        time.sleep(0.5)
                        try:
                            ser = _serial.Serial(port, 115200, timeout=1)
                            time.sleep(1.2)
                            ser.write(f"TIME:{int(time.time())}\n".encode())
                            time.sleep(0.2); ser.readline()
                        except Exception as e2:
                            status = f"DISCONNECTED: {e2}"
                            break
                        break
                    if l == "END": break
                    if "|" in l: lines.append(l)
                if lines:
                    codes = lines
                    status = "LIVE"
            except Exception as e:
                status = f"ERR: {e}"

        stdscr.erase()
        h, w = stdscr.getmaxyx()
        if h < 5 or w < 30:
            try: stdscr.addstr(0, 0, "Terminal too small")
            except: pass
            stdscr.refresh()
            continue

        # Header
        header = f"  PYAUTH  •  {port}  •  q to quit"
        try:
            stdscr.addstr(0, 0, header.ljust(w)[:w-1], curses.color_pair(4) | curses.A_BOLD)
            stdscr.addstr(1, 0, ("─" * (w-1))[:w-1], curses.A_DIM)
        except: pass

        if not codes:
            try: stdscr.addstr(3, 2, "(empty vault - no codes)", curses.A_DIM)
            except: pass
        else:
            for i, item in enumerate(codes):
                y = 2 + i
                if y >= h - 2: break
                try:
                    n, c, r = item.split("|")
                except: continue
                try:
                    stdscr.addstr(y, 2, f"{n:<20}"[:20])
                    stdscr.addstr(y, 24, f"{c}", curses.color_pair(1) | curses.A_BOLD)
                    if r.isdigit():
                        secs = int(r)
                        color = curses.color_pair(2) if secs > 10 else curses.color_pair(3)
                        stdscr.addstr(y, 34, f"({secs:>2}s) ", color)
                        if w > 52:
                            bar_len = max(0, int((w - 48) * secs / 30))
                            stdscr.addstr(y, 42, "█" * bar_len, color)
                    else:
                        stdscr.addstr(y, 34, "(stored)", curses.A_DIM)
                except curses.error:
                    pass

        # Footer pinned to bottom
        try:
            stdscr.addstr(h-1, 0, ("─" * (w-1))[:w-1], curses.A_DIM)
            stdscr.addstr(h-1, 2, f" {status} • updates every 1s ", curses.A_DIM)
        except: pass
        stdscr.refresh()


# ---------- FULL TUI APP ----------
def _tui_fetch_codes(ser):
    ser.reset_input_buffer()
    ser.write(b"GET\n")
    out=[]; start=time.time()
    while time.time()-start < 1.0:
        l=ser.readline().decode(errors='ignore').strip()
        if l=="END": break
        if "|" in l: out.append(l)
    return out

def _tui_fetch_names(ser):
    ser.reset_input_buffer()
    ser.write(b"LIST\n")
    out=[]; start=time.time()
    while time.time()-start < 1.5:
        l=ser.readline().decode(errors='ignore').strip()
        if l=="ENDLIST": break
        if l and ":" not in l and "|" not in l and "READY" not in l and "OK" not in l and "ERR" not in l and l:
            out.append(l)
    return out

def _tui_copy(text):
    import subprocess, shutil
    for cmd in (["wl-copy"], ["xclip","-selection","clipboard"], ["xsel","--clipboard","--input"], ["pbcopy"]):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, input=text.encode(), timeout=1, check=False)
                return True
            except Exception: pass
    return False

def _tui_input(stdscr, y, x, w, prompt, initial="", password=False):
    import curses
    curses.curs_set(1)
    buf=list(initial); pos=len(buf)
    while True:
        stdscr.addstr(y, x, prompt)
        # clear field area
        stdscr.addstr(y, x+len(prompt), " "*(w-len(prompt)))
        disp="".join(buf)
        if password: disp="*"*len(disp)
        stdscr.addstr(y, x+len(prompt), disp[:w-len(prompt)-1])
        stdscr.move(y, min(x+len(prompt)+pos, x+w-1))
        stdscr.refresh()
        k=stdscr.getch()
        if k in (10,13): # Enter
            curses.curs_set(0); return "".join(buf)
        if k==27: # Esc
            curses.curs_set(0); return None
        if k in (127, curses.KEY_BACKSPACE, 8):
            if pos>0: del buf[pos-1]; pos-=1
        elif k==curses.KEY_LEFT:
            pos=max(0,pos-1)
        elif k==curses.KEY_RIGHT:
            pos=min(len(buf),pos+1)
        elif k==curses.KEY_DC:
            if pos<len(buf): del buf[pos]
        elif 32 <= k <= 126:
            if len(buf)<200: buf.insert(pos, chr(k)); pos+=1

def cmd_tui():
    import curses
    ser, port = connect()
    try: curses.wrapper(_tui_main, ser, port)
    except KeyboardInterrupt: pass
    finally:
        try: ser.close()
        except: pass

def _tui_main(stdscr, ser, port):
    import curses
    curses.curs_set(0)
    stdscr.nodelay(True); stdscr.timeout(150)
    curses.use_default_colors()
    try: curses.start_color()
    except: pass
    curses.init_pair(1, curses.COLOR_WHITE, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_RED, -1)
    curses.init_pair(4, curses.COLOR_CYAN, -1)
    curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_CYAN) # selected
    curses.init_pair(6, curses.COLOR_YELLOW, -1)
    curses.init_pair(7, curses.COLOR_MAGENTA, -1)

    mode="codes"  # codes | add | manage | confirm
    codes=[]; names=[]
    sel=0; search=""; status="LIVE"; msg=""; msg_t=0
    last_fetch=0
    # add form state
    add_fields=["name","","secret","","type","totp"]
    add_idx=0
    confirm_name=""

    def set_msg(t):
        nonlocal msg, msg_t
        msg=t; msg_t=time.time()

    while True:
        h,w = stdscr.getmaxyx()
        key=stdscr.getch()

        # ---- global keys ----
        if mode=="codes":
            if key in (ord('q'), ord('Q')): break
            if key==ord('a'): mode="add"; add_fields=["name","","secret","","type","totp"]; add_idx=0; continue
            if key==ord('d') and codes:
                # delete selected code entry
                try: confirm_name=codes[sel].split("|")[0]
                except: confirm_name=""
                mode="confirm"; continue
            if key==ord('m'): mode="manage"; names=_tui_fetch_names(ser); sel=0; continue
            if key==ord('/'):
                stdscr.nodelay(False)
                s=_tui_input(stdscr, h-2, 2, w-4, "Search: ", search)
                stdscr.nodelay(True); stdscr.timeout(150)
                if s is not None: search=s; sel=0
                continue
            if key==curses.KEY_UP: sel=max(0,sel-1)
            if key==curses.KEY_DOWN: sel=min(max(0,len(codes)-1),sel+1)
            if key in (10,13) and codes:
                try:
                    code=codes[sel].split("|")[1]
                    ok=_tui_copy(code)
                    set_msg(f"Copied {codes[sel].split('|')[0]} {'to clipboard' if ok else '(no clipboard tool: wl-copy/xclip)'}")
                except: pass
            if key==ord('r'):
                last_fetch=0; set_msg("Refreshed")
        elif mode=="manage":
            if key==27: mode="codes"; sel=0; continue
            if key in (ord('q'),): mode="codes"; continue
            if key==curses.KEY_UP: sel=max(0,sel-1)
            if key==curses.KEY_DOWN: sel=min(max(0,len(names)-1),sel+1)
            if key==ord('d') and names:
                confirm_name=names[sel]; mode="confirm"; continue
            if key==ord('r'): names=_tui_fetch_names(ser); set_msg("Refreshed list")
        elif mode=="confirm":
            if key in (ord('y'), ord('Y')):
                try:
                    ser.reset_input_buffer(); ser.write(f"DEL:{confirm_name}\n".encode())
                    res=ser.readline().decode(errors='ignore').strip()
                    set_msg(res or f"Deleted {confirm_name}")
                except Exception as e: set_msg(f"ERR: {e}")
                mode="codes"; sel=0; last_fetch=0
            elif key in (ord('n'), ord('N'), 27):
                mode="codes"
        elif mode=="add":
            if key==27: mode="codes"; continue
            if key==9: # Tab -> next field
                add_idx=(add_idx+1)%3; continue
            if key==curses.KEY_UP: add_idx=max(0,add_idx-1); continue
            if key==curses.KEY_DOWN: add_idx=min(2,add_idx+1); continue
            if key in (10,13):
                # Enter on a field -> edit it, Enter on last field -> submit if all filled?
                # Edit current field
                labels=["Name: ","Secret / otpauth URI: ","Type (totp/pass): "]
                cur = add_fields[add_idx*2+1] if add_idx<3 else ""
                # For type field, toggle instead of typing
                if add_idx==2:
                    add_fields[5]="pass" if add_fields[5]=="totp" else "totp"
                    continue
                stdscr.nodelay(False)
                val=_tui_input(stdscr, 6+add_idx*2, 2, w-4, labels[add_idx], cur, password=(add_idx==1))
                stdscr.nodelay(True); stdscr.timeout(150)
                if val is not None:
                    add_fields[add_idx*2+1]=val
                    if add_idx<2: add_idx+=1
                    else:
                        pass # stay, user presses Ctrl+S / Enter again? handled below
                continue
            if key==19: # Ctrl+S submit
                name=add_fields[1].strip(); secret_raw=add_fields[3].strip(); ftype=add_fields[5].strip() or "totp"
                if not name and secret_raw.startswith("otpauth://"):
                    parsed=parse_otpauth(secret_raw)
                    if parsed: name, secret_raw = parsed
                elif secret_raw.startswith("otpauth://"):
                    parsed=parse_otpauth(secret_raw)
                    if parsed:
                        if not name: name=parsed[0]
                        secret_raw=parsed[1]
                if not name or not secret_raw:
                    set_msg("Need NAME + SECRET (or paste otpauth:// URI)"); continue
                ttype=detect_type(secret_raw, ftype if ftype in ("totp","pass") else None)
                secret=secret_raw.upper().strip().replace(" ","") if ttype=="totp" else secret_raw
                try:
                    res=send_add(ser, name, secret, ttype)
                    set_msg(f"{name} -> {res}")
                    mode="codes"; last_fetch=0; sel=0
                except Exception as e: set_msg(f"ERR: {e}")
                continue

        # ---- fetch codes every 1s in codes mode ----
        now=time.time()
        if mode in ("codes","manage") and now-last_fetch>=1.0:
            last_fetch=now
            try: codes=_tui_fetch_codes(ser); status="LIVE"
            except Exception as e: status=f"ERR: {e}"

        # ---- draw ----
        stdscr.erase()
        if h<8 or w<40:
            try: stdscr.addstr(0,0,"Terminal too small")
            except: pass
            stdscr.refresh(); continue
        # header
        try:
            stdscr.addstr(0,0, f"  PYAUTH  •  {port}  •  {mode.upper()}".ljust(w)[:w-1], curses.color_pair(4)|curses.A_BOLD)
            stdscr.addstr(1,0, ("─"*(w-1))[:w-1], curses.A_DIM)
        except: pass

        if mode=="codes":
            # filter
            shown=[c for c in codes if search.lower() in c.split("|")[0].lower()] if search else codes
            if sel>=len(shown): sel=max(0,len(shown)-1)
            if not shown:
                try: stdscr.addstr(3,2,"(empty - press 'a' to add)" if not search else f"No match for '{search}'", curses.A_DIM)
                except: pass
            for i,item in enumerate(shown):
                y=2+i
                if y>=h-3: break
                try: n,c,r=item.split("|")
                except: continue
                is_sel=(i==sel)
                attr=curses.color_pair(5) if is_sel else curses.A_NORMAL
                try:
                    stdscr.addstr(y,2, f"{n:<20}"[:20], attr)
                    stdscr.addstr(y,24, f"{c}", (curses.color_pair(1)|curses.A_BOLD) if not is_sel else attr)
                    if r.isdigit():
                        secs=int(r); col=curses.color_pair(2) if secs>10 else curses.color_pair(3)
                        stdscr.addstr(y,34, f"({secs:>2}s) ", col if not is_sel else attr)
                        if w>52:
                            bar_len=max(0,int((w-48)*secs/30))
                            stdscr.addstr(y,42,"█"*bar_len, col if not is_sel else attr)
                    else: stdscr.addstr(y,34,"(stored)", curses.A_DIM if not is_sel else attr)
                except curses.error: pass
            footer=" ↑↓ navigate • Enter copy • a add • d delete • m manage • / search • r refresh • q quit "
            if search: footer+=f" • filter: {search} (Esc in search clears)"
        elif mode=="manage":
            try: stdscr.addstr(2,2,"MANAGE VAULT — select entry, 'd' to delete, Esc/q back", curses.A_BOLD)
            except: pass
            for i,n in enumerate(names):
                y=4+i
                if y>=h-3: break
                attr=curses.color_pair(5) if i==sel else curses.A_NORMAL
                try: stdscr.addstr(y,4,f"• {n}", attr)
                except: pass
            if not names:
                try: stdscr.addstr(4,4,"(empty)", curses.A_DIM)
                except: pass
            footer=" ↑↓ navigate • d delete • r refresh • Esc back "
        elif mode=="confirm":
            try:
                stdscr.addstr(4,2,f"Delete '{confirm_name}' ?", curses.color_pair(3)|curses.A_BOLD)
                stdscr.addstr(6,2,"Press [y] yes  /  [n] no", curses.A_DIM)
            except: pass
            footer=" y confirm • n cancel "
        elif mode=="add":
            labels=["Name: ","Secret / otpauth URI: ","Type (totp/pass): "]
            try:
                stdscr.addstr(2,2,"ADD NEW ENTRY — Tab/↑↓ move, Enter edit, Ctrl+S save, Esc cancel", curses.A_BOLD)
                stdscr.addstr(3,2,"Tip: paste a full otpauth:// URI as Secret and Name auto-fills", curses.A_DIM)
                for i in range(3):
                    y=6+i*2
                    val=add_fields[i*2+1]
                    disp=("*"*len(val)) if i==1 and val else val
                    attr=curses.color_pair(5) if i==add_idx else curses.A_NORMAL
                    stdscr.addstr(y,2,labels[i], attr)
                    stdscr.addstr(y,2+len(labels[i]), disp[:w-len(labels[i])-4], attr)
                stdscr.addstr(13,2,"[ Ctrl+S ] Save    [ Esc ] Cancel    [ Tab ] Next field", curses.color_pair(6))
            except: pass
            footer=" Tab next • Enter edit • Ctrl+S save • Esc cancel "


        try:
            if msg and time.time()-msg_t<4:
                stdscr.addstr(h-3,2,msg[:w-4], curses.color_pair(6))
            stdscr.addstr(h-2,0, ("─"*(w-1))[:w-1], curses.A_DIM)
            stdscr.addstr(h-1,2, footer[:w-4], curses.A_DIM)
            if mode=="codes": stdscr.addstr(h-1, max(2,w-18), f" {status} ", curses.A_DIM)
        except: pass
        stdscr.refresh()


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

def main():
    parser=argparse.ArgumentParser(prog="pyauth")
    sub=parser.add_subparsers(dest="cmd")
    sub.add_parser("list")
    a=sub.add_parser("add"); a.add_argument("name"); a.add_argument("secret"); a.add_argument("-t","--type",choices=["totp","pass"],default=None)
    r=sub.add_parser("remove"); r.add_argument("name")
    b=sub.add_parser("bulk"); b.add_argument("file"); b.add_argument("-t","--type",choices=["totp","pass"],default=None)
    sub.add_parser("codes"); sub.add_parser("show"); sub.add_parser("clear"); sub.add_parser("tui")
    args=parser.parse_args()
    if not args.cmd or args.cmd=="tui": cmd_tui()
    elif args.cmd=="show": cmd_show()
    elif args.cmd=="list": cmd_list()
    elif args.cmd=="add": cmd_add(args.name, args.secret, args.type)
    elif args.cmd=="remove": cmd_remove(args.name)
    elif args.cmd=="bulk": cmd_bulk(args.file, args.type)
    elif args.cmd=="codes": cmd_codes()
    elif args.cmd=="clear":
        ser,port=connect(); ser.write(b"CLEAR\n"); print(f"{Fore.YELLOW}{ser.readline().decode().strip()}{Style.RESET_ALL}"); ser.close()

if __name__ == "__main__":
    main()

