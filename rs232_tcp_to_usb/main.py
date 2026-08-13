import sys
import os
import re
import time
import socket
import threading
import queue
import csv
import datetime
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

# Safe Excel Support Importing
try:
    import openpyxl
    HAS_OPENPYXL = True
except Exception:
    HAS_OPENPYXL = False

# Safe Keyboard Driver Importing
try:
    import keyboard
    HAS_KEYBOARD = True
except Exception:
    HAS_KEYBOARD = False

try:
    from pynput.keyboard import Controller, Key
    pynput_keyboard = Controller()
    HAS_PYNPUT = True
except Exception:
    HAS_PYNPUT = False

# Try importing serial
try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except Exception:
    HAS_SERIAL = False

# -------------------------------------------------------------
# FILE LOGGING UTILITIES
# -------------------------------------------------------------
def log_to_txt(filepath, text_value):
    """Appends raw received text with a simple timestamp prefix to a txt file."""
    try:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(f"[{now_str}] {text_value}\n")
    except Exception as e:
        print(f"[TXT LOG ERROR] {e}")

def log_to_csv(filepath, text_value):
    """Appends a structured row with a timestamp and the received value to a CSV file."""
    try:
        file_exists = os.path.exists(filepath)
        with open(filepath, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "Received Data"])
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            writer.writerow([now_str, text_value])
    except Exception as e:
        print(f"[CSV LOG ERROR] {e}")

def log_to_xlsx(filepath, text_value):
    """Appends a structured row with a timestamp and the received value to an Excel file."""
    if not HAS_OPENPYXL:
        print("[XLSX LOG ERROR] openpyxl package not available, falling back to CSV log style")
        csv_fallback_path = os.path.splitext(filepath)[0] + "_fallback.csv"
        log_to_csv(csv_fallback_path, text_value)
        return

    try:
        if os.path.exists(filepath):
            wb = openpyxl.load_workbook(filepath)
            ws = wb.active
        else:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(["Timestamp", "Received Data"])

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        ws.append([now_str, text_value])
        wb.save(filepath)
    except Exception as e:
        print(f"[XLSX LOG ERROR] {e}")

# -------------------------------------------------------------
# CONSTANTS & CONFIGURATION
# -------------------------------------------------------------
VERSION = "v1.0.0"

CONTROL_CHARS = {
    0: '[NUL]', 1: '[SOH]', 2: '[STX]', 3: '[ETX]', 4: '[EOT]', 5: '[ENQ]', 6: '[ACK]',
    7: '[BEL]', 8: '[BS]', 9: '[TAB]', 10: '[LF]', 11: '[VT]', 12: '[FF]', 13: '[CR]',
    14: '[SO]', 15: '[SI]', 16: '[DLE]', 17: '[DC1]', 18: '[DC2]', 19: '[DC3]', 20: '[DC4]',
    21: '[NAK]', 22: '[SYN]', 23: '[ETB]', 24: '[CAN]', 25: '[EM]', 26: '[SUB]', 27: '[ESC]',
    28: '[FS]', 29: '[GS]', 30: '[RS]', 31: '[US]', 127: '[DEL]'
}

# -------------------------------------------------------------
# KEYBOARD WEDGE SIMULATOR
# -------------------------------------------------------------
def trigger_key(key_name):
    """Sends a physical keystroke safely."""
    print(f"[WEDGE KEY] {key_name.upper()}")
    if HAS_KEYBOARD:
        try:
            keyboard.send(key_name)
            return
        except Exception:
            pass
    if HAS_PYNPUT:
        try:
            if key_name == 'enter':
                pynput_keyboard.press(Key.enter)
                pynput_keyboard.release(Key.enter)
            elif key_name == 'tab':
                pynput_keyboard.press(Key.tab)
                pynput_keyboard.release(Key.tab)
            elif key_name == 'esc':
                pynput_keyboard.press(Key.esc)
                pynput_keyboard.release(Key.esc)
            elif key_name == 'space':
                pynput_keyboard.press(Key.space)
                pynput_keyboard.release(Key.space)
            return
        except Exception:
            pass

def trigger_text(text):
    """Types standard text characters."""
    if not text:
        return
    print(f"[WEDGE TEXT] {text}")
    if HAS_KEYBOARD:
        try:
            keyboard.write(text)
            return
        except Exception:
            pass
    if HAS_PYNPUT:
        try:
            pynput_keyboard.type(text)
            return
        except Exception:
            pass

def simulate_keyboard_chars(text):
    """Simulates keyboard input for characters, handling tabs/newlines/escapes."""
    # Normalize CRLF to a single newline to prevent double ENTER simulated keypresses
    text = text.replace('\r\n', '\n')
    buffer = []
    for char in text:
        if char in ('\r', '\n', '\t'):
            if buffer:
                trigger_text("".join(buffer))
                buffer.clear()
            if char == '\t':
                trigger_key('tab')
            elif char == '\r' or char == '\n':
                trigger_key('enter')
        else:
            if ord(char) >= 32 or char.isspace():
                buffer.append(char)
    if buffer:
        trigger_text("".join(buffer))

def parse_and_simulate(raw_str):
    """Parses prefix/suffix strings for special codes and types them."""
    # Resolve standard backslash escapes
    s = raw_str.replace('\\r\\n', '\n').replace('\\r', '\r').replace('\\n', '\n').replace('\\t', '\t')
    # Normalize potential physical CRLF sequences
    s = s.replace('\r\n', '\n')

    # Process bracketed tags like [ENTER], [TAB], [ESC], [SPACE]
    tokens = re.split(r'(\[[A-Z0-9_]+\])', s)
    for token in tokens:
        if not token:
            continue
        if token.startswith('[') and token.endswith(']'):
            tag = token[1:-1].upper()
            if tag == 'ENTER':
                trigger_key('enter')
            elif tag == 'TAB':
                trigger_key('tab')
            elif tag == 'ESC' or tag == 'ESCAPE':
                trigger_key('esc')
            elif tag == 'SPACE':
                trigger_key('space')
            else:
                trigger_text(token)
        else:
            simulate_keyboard_chars(token)

# -------------------------------------------------------------
# SPECIAL CHARACTERS FORMATTING
# -------------------------------------------------------------
def format_received_data(text, show_special):
    """Formats received data string for visual display in UI."""
    if not show_special:
        return text

    formatted = []
    for char in text:
        code = ord(char)
        if code in CONTROL_CHARS:
            formatted.append(CONTROL_CHARS[code])
        elif code < 32 or code == 127:
            formatted.append(f'\\x{code:02X}')
        else:
            formatted.append(char)
    return "".join(formatted)

# -------------------------------------------------------------
# THREADED CONNECTION WORKER
# -------------------------------------------------------------
class ConnectionWorker:
    def __init__(self, app):
        self.app = app
        self.running = False
        self.thread = None
        self.serial_port = None
        self.tcp_socket = None

    def start_rs232(self, port, baud, parity, bytesize, stopbits):
        self.running = True
        self.thread = threading.Thread(
            target=self._rs232_loop,
            args=(port, baud, parity, bytesize, stopbits),
            daemon=True
        )
        self.thread.start()

    def start_tcp(self, host, port):
        self.running = True
        self.thread = threading.Thread(
            target=self._tcp_loop,
            args=(host, port),
            daemon=True
        )
        self.thread.start()

    def stop(self):
        self.running = False
        # Terminate sockets or serial ports to break out of blocking operations
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception:
                pass
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except Exception:
                pass

    def _rs232_loop(self, port, baud, parity, bytesize, stopbits):
        if not HAS_SERIAL:
            self.app.update_status("Error: pyserial not installed", "red")
            self.app.handle_disconnect_event()
            return

        parity_map = {
            'None': serial.PARITY_NONE,
            'Even': serial.PARITY_EVEN,
            'Odd': serial.PARITY_ODD,
            'Mark': serial.PARITY_MARK,
            'Space': serial.PARITY_SPACE
        }
        bytesize_map = {
            '5': serial.FIVEBITS,
            '6': serial.SIXBITS,
            '7': serial.SEVENBITS,
            '8': serial.EIGHTBITS
        }
        stopbits_map = {
            '1': serial.STOPBITS_ONE,
            '1.5': serial.STOPBITS_ONE_POINT_FIVE,
            '2': serial.STOPBITS_TWO
        }

        p_val = parity_map.get(parity, serial.PARITY_NONE)
        b_val = bytesize_map.get(str(bytesize), serial.EIGHTBITS)
        s_val = stopbits_map.get(str(stopbits), serial.STOPBITS_ONE)

        while self.running:
            self.app.update_status(f"CONNECTING to {port}...", "orange")
            try:
                self.serial_port = serial.Serial(
                    port=port,
                    baudrate=int(baud),
                    parity=p_val,
                    bytesize=b_val,
                    stopbits=s_val,
                    timeout=1.0
                )
                self.app.update_status("CONNECTED", "green")

                while self.running:
                    if self.serial_port.in_waiting > 0:
                        data = self.serial_port.read(self.serial_port.in_waiting)
                        if data:
                            self.app.handle_data_received(data)
                    else:
                        time.sleep(0.05)
            except Exception as e:
                if not self.running:
                    break
                self.app.update_status(f"CONNECTING... (Error: {str(e)[:50]})", "orange")
                # Auto-reconnection delay
                time.sleep(3)

        self.app.update_status("DISCONNECTED", "red")

    def _tcp_loop(self, host, port):
        while self.running:
            self.app.update_status(f"CONNECTING to {host}:{port}...", "orange")
            try:
                self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.tcp_socket.settimeout(2.0)
                self.tcp_socket.connect((host, int(port)))
                self.app.update_status("CONNECTED", "green")

                self.tcp_socket.settimeout(1.0)
                while self.running:
                    try:
                        data = self.tcp_socket.recv(4096)
                        if not data:
                            raise socket.error("Connection closed by server")
                        self.app.handle_data_received(data)
                    except socket.timeout:
                        continue
            except Exception as e:
                if not self.running:
                    break
                self.app.update_status(f"CONNECTING... (Error: {str(e)[:50]})", "orange")
                if self.tcp_socket:
                    try:
                        self.tcp_socket.close()
                    except Exception:
                        pass
                # Auto-reconnection delay
                time.sleep(3)

        self.app.update_status("DISCONNECTED", "red")


# -------------------------------------------------------------
# APP INTERFACE (GUI)
# -------------------------------------------------------------
class RS232TCPToUSBApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window styling
        self.title("RS232-TCP to USB-KBD Wedge")
        self.geometry("580x700")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Connection variables
        self.connection_type = tk.StringVar(value="RS232")
        self.worker = ConnectionWorker(self)
        self.last_received_bytes = b""

        # Thread-safe formatting state
        self.prefix_value = ""
        self.suffix_value = ""

        # Thread-safe file logging state
        self.saved_file_path = ""
        self.log_file_enabled = False

        # Thread-safe sequential wedge queue
        self.wedge_queue = queue.Queue()
        self.wedge_thread = threading.Thread(target=self._wedge_queue_consumer, daemon=True)
        self.wedge_thread.start()

        # Main layout construction
        self.build_ui()
        self.refresh_com_ports()

        # Initialize thread-safe formatting strings from UI values
        self.update_wedge_formats()

        # Bind window close confirmation catcher
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        """Prompt confirmation before exiting the application."""
        if messagebox.askyesno("Exit Confirmation", "Are you sure you want to close the application?\nAny active connection will be disconnected."):
            # Clean up background connection worker
            try:
                self.worker.stop()
            except Exception:
                pass
            self.destroy()

    def build_ui(self):
        # 1. Header Frame
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=25, pady=(20, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text="RS232-TCP to USB Keyboard Wedge",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold")
        )
        title_label.pack(side="left")

        version_badge = ctk.CTkLabel(
            header_frame,
            text=VERSION,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#1f538d",
            text_color="white",
            corner_radius=8,
            width=55,
            height=20
        )
        version_badge.pack(side="right", padx=(10, 0))

        # Divider line
        divider = ctk.CTkFrame(self, height=2, fg_color="#2e2e2e")
        divider.pack(fill="x", padx=25, pady=5)

        # 2. Connection Type Selection Frame
        conn_selector_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1a1a1a")
        conn_selector_frame.pack(fill="x", padx=25, pady=5)

        conn_label = ctk.CTkLabel(
            conn_selector_frame,
            text="Choose Input Connection Type:",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        )
        conn_label.pack(pady=(8, 4), padx=15, anchor="w")

        radio_container = ctk.CTkFrame(conn_selector_frame, fg_color="transparent")
        radio_container.pack(fill="x", padx=15, pady=(0, 8))

        self.radio_rs232 = ctk.CTkRadioButton(
            radio_container,
            text="RS232 Serial Port",
            variable=self.connection_type,
            value="RS232",
            command=self.toggle_connection_panels,
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.radio_rs232.pack(side="left", expand=True, fill="x", padx=5)

        self.radio_tcp = ctk.CTkRadioButton(
            radio_container,
            text="TCP/IP Client Connection",
            variable=self.connection_type,
            value="TCP",
            command=self.toggle_connection_panels,
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.radio_tcp.pack(side="left", expand=True, fill="x", padx=5)

        # 3. Parameter Panel Container (fixed height for 100% consistent sizing)
        self.params_container = ctk.CTkFrame(self, corner_radius=10, height=145)
        self.params_container.pack(fill="x", padx=25, pady=5)
        self.params_container.pack_propagate(False)

        # 3A. RS232 Sub-panel
        self.rs232_panel = ctk.CTkFrame(self.params_container, fg_color="transparent")

        # Grid Configuration for RS232
        self.rs232_panel.columnconfigure(0, weight=1)
        self.rs232_panel.columnconfigure(1, weight=2)

        # COM Port Dropdown and Refresh
        ctk.CTkLabel(self.rs232_panel, text="COM Port:", font=ctk.CTkFont(family="Segoe UI", size=12)).grid(row=0, column=0, sticky="w", padx=15, pady=4)
        com_action_frame = ctk.CTkFrame(self.rs232_panel, fg_color="transparent")
        com_action_frame.grid(row=0, column=1, sticky="we", padx=15, pady=4)

        self.com_dropdown = ctk.CTkOptionMenu(
            com_action_frame,
            values=["Scanning..."],
            width=130,
            fg_color="#357ec7",
            button_color="#357ec7",
            button_hover_color="#2b6fb5"
        )
        self.com_dropdown.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_refresh = ctk.CTkButton(com_action_frame, text="Refresh", width=70, command=self.refresh_com_ports)
        self.btn_refresh.pack(side="right")

        # Baud Rate & Framing grouped horizontally on a single line
        ctk.CTkLabel(self.rs232_panel, text="Baud/Frame:", font=ctk.CTkFont(family="Segoe UI", size=12)).grid(row=1, column=0, sticky="w", padx=15, pady=4)
        baud_frame_row = ctk.CTkFrame(self.rs232_panel, fg_color="transparent")
        baud_frame_row.grid(row=1, column=1, sticky="we", padx=15, pady=4)

        self.baud_dropdown = ctk.CTkOptionMenu(
            baud_frame_row,
            values=["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"],
            width=80,
            fg_color="#357ec7",
            button_color="#357ec7",
            button_hover_color="#2b6fb5"
        )
        self.baud_dropdown.set("9600")
        self.baud_dropdown.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.databits_dropdown = ctk.CTkOptionMenu(
            baud_frame_row,
            values=["5", "6", "7", "8"],
            width=42,
            fg_color="#357ec7",
            button_color="#357ec7",
            button_hover_color="#2b6fb5"
        )
        self.databits_dropdown.set("8")
        self.databits_dropdown.pack(side="left", fill="x", expand=True, padx=4)

        self.parity_dropdown = ctk.CTkOptionMenu(
            baud_frame_row,
            values=["None", "Even", "Odd", "Mark", "Space"],
            width=65,
            fg_color="#357ec7",
            button_color="#357ec7",
            button_hover_color="#2b6fb5"
        )
        self.parity_dropdown.set("None")
        self.parity_dropdown.pack(side="left", fill="x", expand=True, padx=4)

        self.stopbits_dropdown = ctk.CTkOptionMenu(
            baud_frame_row,
            values=["1", "1.5", "2"],
            width=42,
            fg_color="#357ec7",
            button_color="#357ec7",
            button_hover_color="#2b6fb5"
        )
        self.stopbits_dropdown.set("1")
        self.stopbits_dropdown.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Local RS232 Buttons (Row 2 now instead of Row 3)
        self.rs232_btn_frame = ctk.CTkFrame(self.rs232_panel, fg_color="transparent")
        self.rs232_btn_frame.grid(row=2, column=0, columnspan=2, pady=(10, 5), sticky="we")

        self.btn_rs232_connect = ctk.CTkButton(
            self.rs232_btn_frame,
            text="Connect and Send to USB",
            command=self.handle_connect,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#357ec7",
            hover_color="#2b6fb5",
            height=36
        )
        self.btn_rs232_connect.pack(side="left", fill="x", expand=True, padx=(15, 15))

        self.btn_rs232_disconnect = ctk.CTkButton(
            self.rs232_btn_frame,
            text="Disconnect",
            command=self.handle_disconnect,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color="#7a2a2a",
            hover_color="#541c1c",
            height=36
        )

        # 3B. TCP/IP Sub-panel
        self.tcp_panel = ctk.CTkFrame(self.params_container, fg_color="transparent")
        self.tcp_panel.columnconfigure(0, weight=1)
        self.tcp_panel.columnconfigure(1, weight=2)

        # Server Host/IP with same lighter blue UX
        ctk.CTkLabel(self.tcp_panel, text="Server IP Address:", font=ctk.CTkFont(family="Segoe UI", size=12)).grid(row=0, column=0, sticky="w", padx=15, pady=6)
        self.ip_entry = ctk.CTkEntry(
            self.tcp_panel,
            placeholder_text="e.g. 192.168.1.100",
            fg_color="#357ec7",
            border_color="#357ec7",
            text_color="white",
            placeholder_text_color="#e0e8f5"
        )
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.grid(row=0, column=1, sticky="we", padx=15, pady=6)

        # Server Port with same lighter blue UX
        ctk.CTkLabel(self.tcp_panel, text="Server Port:", font=ctk.CTkFont(family="Segoe UI", size=12)).grid(row=1, column=0, sticky="w", padx=15, pady=6)
        self.port_entry = ctk.CTkEntry(
            self.tcp_panel,
            placeholder_text="e.g. 5000",
            fg_color="#357ec7",
            border_color="#357ec7",
            text_color="white",
            placeholder_text_color="#e0e8f5"
        )
        self.port_entry.insert(0, "5000")
        self.port_entry.grid(row=1, column=1, sticky="we", padx=15, pady=6)

        # Local TCP/IP Buttons (compact vertical margins)
        self.tcp_btn_frame = ctk.CTkFrame(self.tcp_panel, fg_color="transparent")
        self.tcp_btn_frame.grid(row=2, column=0, columnspan=2, pady=(10, 5), sticky="we")

        self.btn_tcp_connect = ctk.CTkButton(
            self.tcp_btn_frame,
            text="Connect and Send to USB",
            command=self.handle_connect,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#357ec7",
            hover_color="#2b6fb5",
            height=36
        )
        self.btn_tcp_connect.pack(side="left", fill="x", expand=True, padx=(15, 15))

        self.btn_tcp_disconnect = ctk.CTkButton(
            self.tcp_btn_frame,
            text="Disconnect",
            command=self.handle_disconnect,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color="#7a2a2a",
            hover_color="#541c1c",
            height=36
        )

        # Pack initial panel based on default radio selection
        self.toggle_connection_panels()

        # 4. USB-KBD Wedge Options (Prefix/Suffix)
        wedge_options_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1a1a1a")
        wedge_options_frame.pack(fill="x", padx=25, pady=5)

        options_title = ctk.CTkLabel(
            wedge_options_frame,
            text="Wedge Formatting Options (Prefix & Suffix)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        options_title.pack(pady=(6, 3), padx=15, anchor="w")

        fields_row = ctk.CTkFrame(wedge_options_frame, fg_color="transparent")
        fields_row.pack(fill="x", padx=15, pady=3)

        # Prefix Input
        prefix_cell = ctk.CTkFrame(fields_row, fg_color="transparent")
        prefix_cell.pack(side="left", expand=True, fill="x", padx=(0, 10))
        ctk.CTkLabel(prefix_cell, text="Prefix (Optional):", font=ctk.CTkFont(family="Segoe UI", size=11)).pack(anchor="w")
        self.prefix_entry = ctk.CTkEntry(prefix_cell, placeholder_text="e.g. [STX] or \\t")
        self.prefix_entry.pack(fill="x", pady=2)
        self.prefix_entry.bind("<KeyRelease>", self.update_wedge_formats)
        self.prefix_entry.bind("<FocusOut>", self.update_wedge_formats)

        # Suffix Input
        suffix_cell = ctk.CTkFrame(fields_row, fg_color="transparent")
        suffix_cell.pack(side="right", expand=True, fill="x", padx=(10, 0))
        ctk.CTkLabel(suffix_cell, text="Suffix (Optional):", font=ctk.CTkFont(family="Segoe UI", size=11)).pack(anchor="w")
        self.suffix_entry = ctk.CTkEntry(suffix_cell, placeholder_text="e.g. \\r\\n")
        self.suffix_entry.insert(0, "\\r\\n")
        self.suffix_entry.pack(fill="x", pady=2)
        self.suffix_entry.bind("<KeyRelease>", self.update_wedge_formats)
        self.suffix_entry.bind("<FocusOut>", self.update_wedge_formats)

        # Tip label for escape sequences and special tags
        tip_label = ctk.CTkLabel(
            wedge_options_frame,
            text="💡 Tip: Supports standard escapes (\\r, \\n, \\t) and tags ([ENTER], [TAB], [ESC], [SPACE]).",
            font=ctk.CTkFont(family="Segoe UI", size=10, slant="italic"),
            text_color="#888888"
        )
        tip_label.pack(pady=(0, 5), padx=15, anchor="w")

        # 5. Save Incoming Data to File Options
        save_file_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1a1a1a")
        save_file_frame.pack(fill="x", padx=25, pady=5)

        save_title = ctk.CTkLabel(
            save_file_frame,
            text="Save Incoming Data to File Options",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        save_title.pack(pady=(6, 3), padx=15, anchor="w")

        # Checkbox for activation
        self.save_to_file_enabled = tk.BooleanVar(value=False)
        self.chk_save_file = ctk.CTkCheckBox(
            save_file_frame,
            text="Enable Logging to File",
            variable=self.save_to_file_enabled,
            command=self.toggle_save_file,
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.chk_save_file.pack(padx=15, pady=3, anchor="w")

        # File Selection row (hidden until enabled)
        self.file_path_frame = ctk.CTkFrame(save_file_frame, fg_color="transparent")

        self.file_path_entry = ctk.CTkEntry(
            self.file_path_frame,
            placeholder_text="No file selected...",
            state="readonly",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.file_path_entry.pack(side="left", fill="x", expand=True, padx=(15, 10), pady=(0, 5))

        self.btn_browse = ctk.CTkButton(
            self.file_path_frame,
            text="Browse",
            command=self.browse_save_file,
            width=80,
            height=28,
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.btn_browse.pack(side="right", padx=(0, 15), pady=(0, 5))

        # 6. Status & Monitor Frame
        monitor_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#111111")
        monitor_frame.pack(fill="x", padx=25, pady=5)

        monitor_title_row = ctk.CTkFrame(monitor_frame, fg_color="transparent")
        monitor_title_row.pack(fill="x", padx=15, pady=(6, 2))

        monitor_title_lbl = ctk.CTkLabel(
            monitor_title_row,
            text="Last Received Data Preview",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        monitor_title_lbl.pack(side="left")

        # Show Special Characters Checkbox
        self.show_special_chars = tk.BooleanVar(value=True)
        self.chk_special = ctk.CTkCheckBox(
            monitor_frame,
            text="Show Special Characters (e.g. [CR], [LF])",
            variable=self.show_special_chars,
            command=self.update_monitor_view,
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.chk_special.pack(padx=15, pady=3, anchor="w")

        # Single-line Data Entry Field
        self.monitor_field = ctk.CTkEntry(
            monitor_frame,
            placeholder_text="Waiting for incoming data stream...",
            state="readonly",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#5cc5e6"
        )
        self.monitor_field.pack(fill="x", padx=15, pady=(3, 8))

        # 6. Controls Section (Buttons & Status Circle)
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.pack(fill="x", padx=25, pady=5)

        # Status Circle Indicator container (Centered nicely)
        self.status_container = ctk.CTkFrame(controls_frame, fg_color="transparent")
        self.status_container.pack(anchor="center", pady=5)

        # Small status canvas to draw a colored dot
        self.status_canvas = tk.Canvas(self.status_container, width=20, height=20, bg="#1a1a1a", highlightthickness=0)
        self.status_canvas.pack(side="left", padx=(10, 5))
        self.status_dot = self.status_canvas.create_oval(3, 3, 17, 17, fill="red", outline="")

        self.status_text_lbl = ctk.CTkLabel(
            self.status_container,
            text="DISCONNECTED",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="red"
        )
        self.status_text_lbl.pack(side="right")

    # -------------------------------------------------------------
    # CONTROL LOGIC / ACTIONS
    # -------------------------------------------------------------
    def toggle_connection_panels(self):
        """Switches between showing the RS232 panel and the TCP panel."""
        choice = self.connection_type.get()
        if choice == "RS232":
            self.tcp_panel.pack_forget()
            self.rs232_panel.pack(fill="both", expand=True, padx=10, pady=10)
        else:
            self.rs232_panel.pack_forget()
            self.tcp_panel.pack(fill="both", expand=True, padx=10, pady=10)

    def refresh_com_ports(self):
        """Scans the operating system for available COM ports."""
        if not HAS_SERIAL:
            self.com_dropdown.configure(values=["No COM Driver"])
            self.com_dropdown.set("No COM Driver")
            return

        ports = [p.device for p in serial.tools.list_ports.comports()]
        if ports:
            # Sort ports naturally (COM1, COM2, etc.)
            ports.sort(key=lambda x: [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', x)])
            self.com_dropdown.configure(values=ports)
            self.com_dropdown.set(ports[0])
        else:
            self.com_dropdown.configure(values=["No COM Ports Found"])
            self.com_dropdown.set("No COM Ports Found")

    def update_status(self, text, color):
        """Thread-safe UI status updater."""
        self.after(0, self._update_status_ui, text, color)

    def _update_status_ui(self, text, color):
        """Internal helper to apply color/text changes on main thread."""
        hex_color = "red"
        if color == "green":
            hex_color = "#47d147"
        elif color == "orange":
            hex_color = "#ffa500"

        self.status_canvas.itemconfig(self.status_dot, fill=hex_color)
        self.status_text_lbl.configure(text=text, text_color=hex_color)

        conn_mode = self.connection_type.get()

        if color == "green":
            # Successful connection
            if conn_mode == "RS232":
                self.btn_rs232_connect.configure(
                    fg_color="#2b7336",
                    hover_color="#1e5225",
                    text="Connected",
                    state="disabled"
                )
                self.btn_rs232_disconnect.pack(side="left", fill="x", expand=True, padx=(5, 15))
            else:
                self.btn_tcp_connect.configure(
                    fg_color="#2b7336",
                    hover_color="#1e5225",
                    text="Connected",
                    state="disabled"
                )
                self.btn_tcp_disconnect.pack(side="left", fill="x", expand=True, padx=(5, 15))
        elif color == "orange":
            # Connecting state
            if conn_mode == "RS232":
                self.btn_rs232_connect.configure(
                    fg_color="#a86208",
                    hover_color="#7c4705",
                    text="Connecting...",
                    state="disabled"
                )
                self.btn_rs232_disconnect.pack(side="left", fill="x", expand=True, padx=(5, 15))
            else:
                self.btn_tcp_connect.configure(
                    fg_color="#a86208",
                    hover_color="#7c4705",
                    text="Connecting...",
                    state="disabled"
                )
                self.btn_tcp_disconnect.pack(side="left", fill="x", expand=True, padx=(5, 15))
        else:
            # Disconnected or Error state. Restore both to original.
            self.btn_rs232_connect.configure(
                fg_color="#357ec7",
                hover_color="#2b6fb5",
                text="Connect and Send to USB",
                state="normal"
            )
            self.btn_rs232_disconnect.pack_forget()

            self.btn_tcp_connect.configure(
                fg_color="#357ec7",
                hover_color="#2b6fb5",
                text="Connect and Send to USB",
                state="normal"
            )
            self.btn_tcp_disconnect.pack_forget()

    def handle_connect(self):
        """Handles connection action, validating input parameters and launching threads."""
        conn_mode = self.connection_type.get()

        # Disable all UI parameters during connection
        self.toggle_ui_state("disabled")

        if conn_mode == "RS232":
            port = self.com_dropdown.get()
            if port in ("No COM Ports Found", "No COM Driver", "Scanning..."):
                self.update_status("Error: No COM Port selected", "red")
                self.toggle_ui_state("normal")
                return

            baud = self.baud_dropdown.get()
            parity = self.parity_dropdown.get()
            bytesize = self.databits_dropdown.get()
            stopbits = self.stopbits_dropdown.get()

            self.worker.start_rs232(port, baud, parity, bytesize, stopbits)
        else:
            host = self.ip_entry.get().strip()
            port = self.port_entry.get().strip()
            if not host or not port:
                self.update_status("Error: Missing Host/Port", "red")
                self.toggle_ui_state("normal")
                return

            try:
                int(port)
            except ValueError:
                self.update_status("Error: Invalid Port format", "red")
                self.toggle_ui_state("normal")
                return

            self.worker.start_tcp(host, port)

    def handle_disconnect(self):
        """Handles manual disconnection request."""
        self.worker.stop()
        self.handle_disconnect_event()

    def handle_disconnect_event(self):
        """Resets UI widgets after connection termination."""
        self.update_status("DISCONNECTED", "red")
        self.toggle_ui_state("normal")

    def toggle_ui_state(self, state):
        """Toggles configuration elements enabled/disabled depending on active state."""
        self.radio_rs232.configure(state=state)
        self.radio_tcp.configure(state=state)
        self.btn_refresh.configure(state=state)
        self.com_dropdown.configure(state=state)
        self.baud_dropdown.configure(state=state)
        self.databits_dropdown.configure(state=state)
        self.parity_dropdown.configure(state=state)
        self.stopbits_dropdown.configure(state=state)
        self.ip_entry.configure(state=state)
        self.port_entry.configure(state=state)

    def toggle_save_file(self):
        """Called when user toggles 'Enable Logging to File' checkbox."""
        if self.save_to_file_enabled.get():
            # Force disconnect if active
            if self.worker.running:
                messagebox.showwarning("Must disconnect first", "Must disconnect before saving to file")
                self.handle_disconnect()

            # Show file path selection row
            self.file_path_frame.pack(fill="x", pady=(0, 5))
            # If no file path is set, automatically trigger Browse dialog
            if not self.saved_file_path:
                self.browse_save_file()
        else:
            self.file_path_frame.pack_forget()
        self.update_wedge_formats()

    def browse_save_file(self):
        """Opens file dialog with the same modern UX and sets file path."""
        # Force disconnect if active
        if self.worker.running:
            messagebox.showwarning("Must disconnect first", "Must disconnect before saving to file")
            self.handle_disconnect()

        from tkinter import filedialog

        # File types: CSV is default, but TXT and XLSX are also supported.
        filetypes = [
            ("CSV files (*.csv)", "*.csv"),
            ("Text files (*.txt)", "*.txt"),
            ("Excel files (*.xlsx)", "*.xlsx"),
            ("All files (*.*)", "*.*")
        ]

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Select Output Log File",
            defaultextension=".csv",
            filetypes=filetypes
        )

        if path:
            self.saved_file_path = path
            # Update read-only entry field
            self.file_path_entry.configure(state="normal")
            self.file_path_entry.delete(0, "end")
            self.file_path_entry.insert(0, path)
            self.file_path_entry.configure(state="readonly")

            # Make sure checkbox is checked if a file was successfully browsed
            self.save_to_file_enabled.set(True)
            self.file_path_frame.pack(fill="x", pady=(0, 5))
        else:
            # If user cancelled and there's no path, uncheck the box and hide frame
            if not self.saved_file_path:
                self.save_to_file_enabled.set(False)
                self.file_path_frame.pack_forget()

        self.update_wedge_formats()

    def update_wedge_formats(self, event=None):
        """Thread-safely reads values from Prefix and Suffix entries on the main thread."""
        try:
            self.prefix_value = self.prefix_entry.get()
        except Exception:
            self.prefix_value = ""

        try:
            self.suffix_value = self.suffix_entry.get()
        except Exception:
            self.suffix_value = ""

        try:
            self.log_file_enabled = self.save_to_file_enabled.get()
        except Exception:
            self.log_file_enabled = False

    def _wedge_queue_consumer(self):
        """Dedicated background thread loop that sequentializes keyboard wedge typing."""
        while True:
            try:
                # Wait for the next item in the queue
                raw_data_str, prefix_val, suffix_val, log_enabled, log_path = self.wedge_queue.get()

                # 1. Simulate Prefix
                if prefix_val:
                    parse_and_simulate(prefix_val)

                # 2. Simulate Raw Received Data (no strip/clean as requested)
                simulate_keyboard_chars(raw_data_str)

                # 3. Simulate Suffix
                if suffix_val:
                    parse_and_simulate(suffix_val)

                # 4. Log to File if active
                if log_enabled and log_path:
                    ext = os.path.splitext(log_path)[1].lower()
                    if ext == ".xlsx":
                        log_to_xlsx(log_path, raw_data_str)
                    elif ext == ".csv":
                        log_to_csv(log_path, raw_data_str)
                    else:
                        log_to_txt(log_path, raw_data_str)

                self.wedge_queue.task_done()
            except Exception as e:
                print(f"[WEDGE ERROR] {e}")

    def handle_data_received(self, data_bytes):
        """Callback triggered on worker thread upon receiving raw byte packet."""
        self.last_received_bytes = data_bytes

        # Decode data bytes safely
        try:
            text = data_bytes.decode('utf-8', errors='replace')
        except Exception:
            text = data_bytes.decode('latin-1', errors='replace')

        # Enqueue the text along with thread-safe snapshots of prefix/suffix and logging options
        self.wedge_queue.put((text, self.prefix_value, self.suffix_value, self.log_file_enabled, self.saved_file_path))

        # Update monitor UI thread-safely
        self.after(0, self.update_monitor_view)

    def update_monitor_view(self):
        """Updates monitor view textbox in accordance with show_special_chars checkbox."""
        if not self.last_received_bytes:
            return

        try:
            decoded_text = self.last_received_bytes.decode('utf-8', errors='replace')
        except Exception:
            decoded_text = self.last_received_bytes.decode('latin-1', errors='replace')

        show_special = self.show_special_chars.get()
        formatted_text = format_received_data(decoded_text, show_special)

        # Modify entry on main thread
        self.monitor_field.configure(state="normal")
        self.monitor_field.delete(0, "end")
        self.monitor_field.insert(0, formatted_text)
        self.monitor_field.configure(state="readonly")


# -------------------------------------------------------------
# RUN APPLICATION ENTRYPOINT
# -------------------------------------------------------------
if __name__ == "__main__":
    app = RS232TCPToUSBApp()
    app.mainloop()
