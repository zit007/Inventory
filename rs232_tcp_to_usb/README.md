# RS232-TCP to USB-KBD Keyboard Wedge

O aplicație desktop modernă scrisă în Python (folosind CustomTkinter) care captează date dintr-o conexiune RS232 (Serial) sau de la un server TCP/IP (Client) și le simulează sub formă de taste virtuale direct în sistemul de operare (Keyboard Wedge / USB-KBD).

## 🚀 Caracteristici principale

- **Alegere Conexiune:** Selecție rapidă între portul serial (RS232) sau o conexiune TCP/IP de tip Client printr-o interfață modernă cu stil tip HTML (Dark Theme).
- **Meniu RS232 (Serial) avansat:**
  - Selectare port COM detectat automat.
  - Buton **Refresh** pentru a scana din nou porturile COM disponibile.
  - Configurare parametri conexiune: Baud Rate (implicit `9600`), Data Bits (implicit `8`), Parity (implicit `None`), și Stop Bits (implicit `1`).
- **Conexiune TCP/IP Client:**
  - Configurare IP și Port pentru conectarea la un server TCP de unde se citesc datele primite.
- **USB-KBD Wedge & Formatting:**
  - Câmpuri opționale pentru **Prefix** și **Suffix**.
  - Suportă caractere speciale/escape-uri standard: `\r`, `\n`, `\t`.
  - Suportă tag-uri speciale în paranteze drepte pentru simulare taste fizice: `[ENTER]`, `[TAB]`, `[ESC]`, `[SPACE]`.
  - Transmite datele brute (RAW) exact așa cum vin, fără a curăța delimitatoarele.
- **Live Monitor Preview:**
  - Afișează ultima linie de date primită.
  - Opțiune/Bifă în interfață: **"Show Special Characters"** (afișează caracterele invizibile ca tag-uri vizibile, ex: `[CR]`, `[LF]`, `[TAB]`, etc.).
- **Reconectare Automată:**
  - În caz de deconectare neașteptată sau pierdere a legăturii fizice, aplicația încearcă automat să se reconecteze la intervale regulate de timp.
- **Indicator Vizual Animat:**
  - Status de conexiune colorat în timp real: `DISCONNECTED` (roșu), `CONNECTING...` (portocaliu), și `CONNECTED` (verde).
- **Fără Consolă deschisă:**
  - Compilată special pentru a rula silențios ca o aplicație grafică pură în Windows.

---

## 🛠️ Cum se instalează și rulează din surse

### 1. Prerelativități
Aveți nevoie de **Python 3.8 - 3.12** instalat pe sistemul dumneavoastră.

### 2. Instalare dependențe
Deschideți un terminal/command prompt în folderul proiectului și rulați:
```bash
pip install -r requirements.txt
```

### 3. Rulare aplicație
```bash
python main.py
```

---

## 📦 Cum se generează executabilul final (`.exe`) pe Windows

Pentru a compila proiectul într-un singur fișier `.exe` care rulează independent (fără a lăsa o consolă în spate), rulați scriptul automat pus la dispoziție:

1. Dați dublu-click pe fișierul **`build.bat`** aflat în folderul proiectului.
2. Scriptul va instala automat dependențele necesare și va rula `PyInstaller`.
3. La finalul procesului, veți găsi executabilul gata de utilizat în directorul proaspăt creat:
   **`rs232_tcp_to_usb/dist/RS232_TCP_to_USB_Wedge.exe`**

---

## 🔧 Explicare Format Prefix & Suffix

Puteți introduce în câmpurile de formatare atât text literal, cât și coduri speciale:
- Ex: `[TAB]` -> va simula apăsarea tastei fizice TAB.
- Ex: `\r\n` sau `[ENTER]` -> va simula apăsarea tastei fizice ENTER (Carriage Return / Line Feed).
- Ex: `START_` (prefix) și `_END` (suffix) -> va trimite textul respectiv lipit de datele brute recepționate.
