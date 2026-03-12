import pyperclip
from pynput import keyboard
import pyautogui
import tkinter as tk
from tkinter import messagebox
import time
import threading
import requests
import queue
import re


# --- AYARLAR ---
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_ADI = "gemini-3-flash-preview:latest"  # Ana model (F8)
TEXT_MODEL_CANDIDATES = [
    MODEL_ADI,
    "gemini-3-flash-preview:cloud",
]

KISAYOL_METIN = keyboard.Key.f8  # Metin secimi icin kisayol


# Global değişkenler
root = None
gui_queue = queue.Queue()
kisayol_basildi = False


# --- MENÜ SEÇENEKLERİ VE PROMPT'LAR ---
ISLEMLER = {
    "📝 Gramer Düzelt": "Bu metni Türkçe yazım ve dil bilgisi kurallarına göre düzelt, resmi ve akıcı olsun. Sadece sonucu ver.",
    "🇬🇧 İngilizceye Çevir": "Bu metni İngilizceye çevir. Sadece çeviriyi ver.",
    "🇹🇷 Türkçeye Çevir": "Bu metni Türkçeye çevir. Sadece çeviriyi ver.",
    "📑 Özetle (Madde Madde)": "Bu metni analiz et ve en önemli noktaları madde madde özetle.",
    "💼 Daha Resmi Yap": "Bu metni kurumsal bir e-posta diline çevir, çok resmi olsun.",
    "🐍 Python Koduna Çevir": "Bu metindeki isteği yerine getiren bir Python kodu yaz. Sadece kodu ver.",
    "📧 Cevap Yaz (Mail)": "Bu gelen bir e-posta, buna kibar ve profesyonel bir cevap metni taslağı yaz.",
    "🎮 PS5 Oyun Skor + Acımasız Yorum": (
        "Seçili metni bir PS5 oyunu adı olarak ele al. Aşağıdaki formatta Türkçe cevap ver:\n"
        "1) Oyun: <ad>\n"
        "2) Topluluk Beğeni Skorları:\n"
        "- Metacritic User Score: <değer veya 'bilgi yok'>\n"
        "- OpenCritic / benzer eleştirmen ortalaması: <değer veya 'bilgi yok'>\n"
        "- Oyuncu yorumu ortalaması (PS Store vb.): <değer veya 'bilgi yok'>\n"
        "3) Hüküm: sadece 'IYI' veya 'KOTU'\n"
        "4) Acımasız Yorum: 2-4 cümle, net ve sert.\n"
        "Kurallar: Kesin bilmediğin puanı uydurma, onun yerine 'bilgi yok' yaz. "
        "Yorumu skorlarla tutarlı kur."
    ),
    "🧵 Kumaş Miktarı Hesapla": "__KUMASI_HESAPLA__",
}


def get_available_text_model():
    """Metin işlemede kullanılabilir modeli seçer."""
    preferred_models = []
    for model in TEXT_MODEL_CANDIDATES:
        if model and model not in preferred_models:
            preferred_models.append(model)

    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code != 200:
            return MODEL_ADI

        models = response.json().get("models", [])
        installed_lower = {m.get("name", "").lower(): m.get("name", "") for m in models}

        for candidate in preferred_models:
            candidate_lower = candidate.lower()
            if candidate_lower in installed_lower:
                return installed_lower[candidate_lower]

            candidate_base = candidate_lower.split(":")[0]
            for installed_name_lower, installed_name in installed_lower.items():
                if installed_name_lower.startswith(candidate_base + ":"):
                    return installed_name
    except Exception:
        pass

    return MODEL_ADI


def ollama_cevap_al(prompt):
    """Ollama API'den cevap al."""
    try:
        aktif_model = get_available_text_model()
        payload = {
            "model": aktif_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
            },
        }

        response = requests.post(OLLAMA_URL, json=payload, timeout=60)

        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip()

        err_msg = (
            f"Ollama API Hatası: {response.status_code}\n"
            f"Model: {aktif_model}\n"
            f"Cevap: {response.text}"
        )
        print(f"❌ {err_msg}")
        gui_queue.put((messagebox.showerror, ("API Hatası", err_msg)))
        return None

    except requests.exceptions.ConnectionError:
        err_msg = (
            "Ollama'ya bağlanılamadı.\n"
            "Programın çalıştığından emin olun!\n"
            "(http://localhost:11434)"
        )
        print(f"❌ {err_msg}")
        gui_queue.put((messagebox.showerror, ("Bağlantı Hatası", err_msg)))
        return None
    except Exception as e:
        err_msg = f"Beklenmeyen Hata: {e}"
        print(f"❌ {err_msg}")
        gui_queue.put((messagebox.showerror, ("Hata", err_msg)))
        return None


def strip_code_fence(text):
    if not text:
        return text
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:] if lines else []
        while lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def secili_metni_kopyala(max_deneme=4):
    sentinel = f"__AI_ASISTAN__{time.time_ns()}__"
    try:
        pyperclip.copy(sentinel)
    except Exception:
        pass

    for _ in range(max_deneme):
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.2)
        metin = pyperclip.paste()
        if metin and metin.strip() and metin != sentinel:
            return metin
    return ""


def pencere_modunda_gosterilsin_mi(komut_adi):
    return "PS5 Oyun Skor" in komut_adi or "Kumaş Miktarı" in komut_adi


def _metinden_olcu_parse_et(metin):
    """Boy, Kilo ve Kıyafet Türü değerlerini metinden otomatik çeker."""
    boy = kilo = kiyafet = ""
    boy_esle = re.search(
        r"(?:boy|height)\s*[:=]?\s*(\d+(?:[.,]\d+)?)",
        metin, re.IGNORECASE
    )
    kilo_esle = re.search(
        r"(?:kilo|kilo\s*gram|kg|weight)\s*[:=]?\s*(\d+(?:[.,]\d+)?)",
        metin, re.IGNORECASE
    )
    kiyafet_esle = re.search(
        r"(?:k\u0131yafet\s*t\u00fcr\u00fc|kiyafet\s*turu|k\u0131yafet|giysi|clothing|garment)\s*[:=]?\s*([\w\u00e7\u015f\u0131\u011f\u00f6\u00fc\u00c7\u015e\u0130\u011e\u00d6\u00dc ]+)",
        metin, re.IGNORECASE
    )
    if boy_esle:
        boy = boy_esle.group(1).replace(",", ".")
    if kilo_esle:
        kilo = kilo_esle.group(1).replace(",", ".")
    if kiyafet_esle:
        kiyafet = kiyafet_esle.group(1).strip()
    return boy, kilo, kiyafet


def kumasi_hesapla_penceresi_goster(secili_metin):
    """Boy/kilo/kıyafet türü giriş dialogu açarak kumaş miktarını hesaplar."""
    # Seçili metinden değerleri otomatik çek
    parse_boy, parse_kilo, parse_kiyafet = _metinden_olcu_parse_et(secili_metin)
    pencere = tk.Toplevel(root)
    pencere.title("🧵 Kumaş Miktarı Hesapla")
    pencere.geometry("460x400")
    pencere.resizable(False, False)
    pencere.attributes("-topmost", True)
    pencere.configure(bg="#1f1f1f")

    tk.Label(
        pencere, text="🧵 Kumaş Miktarı Hesaplama",
        bg="#1f1f1f", fg="#d4a0ff",
        font=("Segoe UI", 13, "bold")
    ).pack(pady=(18, 4))

    tk.Label(
        pencere,
        text="Seçili metindeki kıyafet bilgisine göre gereken\nkumaş miktarını metre cinsinden hesaplar.",
        bg="#1f1f1f", fg="#aaaaaa",
        font=("Segoe UI", 9),
        justify="center"
    ).pack(pady=(0, 12))

    form_frame = tk.Frame(pencere, bg="#1f1f1f")
    form_frame.pack(padx=30, fill="x")

    def etiket_ve_giris(parent, etiket_metni, placeholder=""):
        satir = tk.Frame(parent, bg="#1f1f1f")
        satir.pack(fill="x", pady=5)
        tk.Label(satir, text=etiket_metni, bg="#1f1f1f", fg="white",
                 font=("Segoe UI", 10), width=16, anchor="w").pack(side="left")
        giris = tk.Entry(satir, bg="#2b2b2b", fg="white", insertbackground="white",
                         font=("Segoe UI", 10), relief="flat", width=20)
        giris.pack(side="left", ipady=4, padx=(4, 0))
        if placeholder:
            giris.insert(0, placeholder)
        return giris

    boy_giris = etiket_ve_giris(form_frame, "Boy (cm):", parse_boy or "örn: 175")
    kilo_giris = etiket_ve_giris(form_frame, "Kilo (kg):", parse_kilo or "örn: 70")
    tur_giris = etiket_ve_giris(form_frame, "Kıyafet Türü:", parse_kiyafet or "örn: gömlek")

    # Otomatik parse başarılıysa kullanıcıya bilgi ver
    if parse_boy or parse_kilo or parse_kiyafet:
        bilgi_label = tk.Label(
            pencere,
            text="✅ Değerler metinden otomatik dolduruldu. İstersen düzenleyebilirsin.",
            bg="#1f1f1f", fg="#78d97a",
            font=("Segoe UI", 8),
            wraplength=400, justify="center"
        )
        bilgi_label.pack(pady=(0, 4))

    sonuc_var = tk.StringVar(value="")
    sonuc_label = tk.Label(
        pencere, textvariable=sonuc_var,
        bg="#1f1f1f", fg="#90ee90",
        font=("Segoe UI", 11, "bold"),
        wraplength=400, justify="center"
    )
    sonuc_label.pack(pady=(14, 4))

    hata_var = tk.StringVar(value="")
    hata_label = tk.Label(
        pencere, textvariable=hata_var,
        bg="#1f1f1f", fg="#ff7070",
        font=("Segoe UI", 9),
        wraplength=400, justify="center"
    )
    hata_label.pack()

    def hesapla():
        boy_str = boy_giris.get().strip()
        kilo_str = kilo_giris.get().strip()
        kiyafet_turu = tur_giris.get().strip()

        if not boy_str or not kilo_str or not kiyafet_turu:
            hata_var.set("❗ Lütfen tüm alanları doldurun.")
            sonuc_var.set("")
            return

        try:
            boy = float(boy_str)
            kilo = float(kilo_str)
        except ValueError:
            hata_var.set("❗ Boy ve kilo sayısal değer olmalıdır.")
            sonuc_var.set("")
            return

        hata_var.set("⏳ Hesaplanıyor...")
        sonuc_var.set("")
        hesapla_btn.config(state="disabled")

        def arka_plan():
            prompt = (
                f"Aşağıdaki metin kıyafet ölçüleri veya kıyafet bilgisi içeriyor:\n\n"
                f"'{secili_metin}'\n\n"
                f"Bu bilgileri ve şu kişisel ölçüleri kullanarak:\n"
                f"- Boy: {boy} cm\n"
                f"- Kilo: {kilo} kg\n"
                f"- Kıyafet türü: {kiyafet_turu}\n\n"
                f"Bu kıyafeti dikmek için gereken kumaş miktarını metre cinsinden hesapla.\n"
                f"Sadece sayısal sonucu ve kısa bir açıklamayı Türkçe ver.\n"
                f"Örnek format: 'Gerekli kumaş miktarı: X.X metre\n[kısa açıklama]'"
            )
            cevap = ollama_cevap_al(prompt)

            def guncelle():
                hesapla_btn.config(state="normal")
                if cevap:
                    hata_var.set("")
                    sonuc_var.set(cevap)
                else:
                    hata_var.set("❌ Hesaplama yapılamadı. Ollama'yı kontrol edin.")
            root.after(0, guncelle)

        threading.Thread(target=arka_plan, daemon=True).start()

    alt_frame = tk.Frame(pencere, bg="#1f1f1f")
    alt_frame.pack(pady=(10, 14))

    hesapla_btn = tk.Button(
        alt_frame, text="🧮 Hesapla", command=hesapla,
        bg="#6a3daa", fg="white",
        activebackground="#7a4dba", activeforeground="white",
        relief="flat", padx=14, pady=6,
        font=("Segoe UI", 10, "bold")
    )
    hesapla_btn.pack(side="left", padx=6)

    tk.Button(
        alt_frame, text="Kapat", command=pencere.destroy,
        bg="#3d3d3d", fg="white",
        activebackground="#4d4d4d", activeforeground="white",
        relief="flat", padx=14, pady=6,
        font=("Segoe UI", 10)
    ).pack(side="left", padx=6)

    pencere.focus_force()
    pencere.lift()


def sonuc_penceresi_goster(baslik, icerik):
    pencere = tk.Toplevel(root)
    pencere.title(baslik)
    pencere.geometry("780x520")
    pencere.minsize(520, 320)
    pencere.attributes("-topmost", True)

    frame = tk.Frame(pencere, bg="#1f1f1f")
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    text_alani = tk.Text(
        frame,
        wrap="word",
        bg="#2b2b2b",
        fg="white",
        insertbackground="white",
        font=("Segoe UI", 10),
        padx=10,
        pady=10,
    )
    kaydirma = tk.Scrollbar(frame, command=text_alani.yview)
    text_alani.configure(yscrollcommand=kaydirma.set)

    text_alani.pack(side="left", fill="both", expand=True)
    kaydirma.pack(side="right", fill="y")

    text_alani.insert("1.0", icerik)
    text_alani.config(state="disabled")

    alt_frame = tk.Frame(pencere, bg="#1f1f1f")
    alt_frame.pack(fill="x", padx=10, pady=(0, 10))

    def panoya_kopyala():
        pyperclip.copy(icerik)

    tk.Button(
        alt_frame,
        text="Panoya Kopyala",
        command=panoya_kopyala,
        bg="#3d3d3d",
        fg="white",
        activebackground="#4d4d4d",
        activeforeground="white",
        relief="flat",
        padx=12,
        pady=6,
    ).pack(side="left")

    tk.Button(
        alt_frame,
        text="Kapat",
        command=pencere.destroy,
        bg="#3d3d3d",
        fg="white",
        activebackground="#4d4d4d",
        activeforeground="white",
        relief="flat",
        padx=12,
        pady=6,
    ).pack(side="right")

    pencere.focus_force()
    pencere.lift()


def islemi_yap(komut_adi, secili_metin):
    # Kumaş hesaplama özel akışı — dialog penceresini ana thread'de aç
    if komut_adi == "🧵 Kumaş Miktarı Hesapla":
        gui_queue.put((kumasi_hesapla_penceresi_goster, (secili_metin,)))
        return

    prompt_emri = ISLEMLER[komut_adi]
    full_prompt = f"{prompt_emri}:\n\n'{secili_metin}'"

    print(f"🤖 İşlem: {komut_adi}")
    print("⏳ Ollama ile işleniyor...")

    sonuc = ollama_cevap_al(full_prompt)
    if not sonuc:
        print("❌ Sonuç alınamadı.")
        return

    sonuc = strip_code_fence(sonuc)
    if sonuc.startswith("'") and sonuc.endswith("'"):
        sonuc = sonuc[1:-1]

    if pencere_modunda_gosterilsin_mi(komut_adi):
        gui_queue.put((sonuc_penceresi_goster, (komut_adi, sonuc)))
        print("✅ Sonuç ayrı pencerede gösterildi.")
        return

    time.sleep(0.2)
    pyperclip.copy(sonuc)
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")
    print("✅ İşlem tamamlandı!")


def process_queue():
    """Kuyruktaki GUI işlemlerini ana thread'de çalıştırır."""
    try:
        while True:
            try:
                task = gui_queue.get_nowait()
            except queue.Empty:
                break
            func, args = task
            func(*args)
    finally:
        if root:
            root.after(100, process_queue)


def menu_goster():
    """Metni kopyalar ve menüyü gösterir (ana thread)."""
    secili_metin = secili_metni_kopyala()
    if not secili_metin.strip():
        gui_queue.put(
            (
                messagebox.showwarning,
                (
                    "Secim Bulunamadi",
                    "Lutfen once metin secin, sonra F8 ile menuyu acin.",
                ),
            )
        )
        return

    menu = tk.Menu(
        root,
        tearoff=0,
        bg="#2b2b2b",
        fg="white",
        activebackground="#4a4a4a",
        activeforeground="white",
        font=("Segoe UI", 10),
    )

    def komut_olustur(k_adi, s_metin):
        def komut_calistir():
            threading.Thread(
                target=islemi_yap, args=(k_adi, s_metin), daemon=True
            ).start()

        return komut_calistir

    for baslik in ISLEMLER.keys():
        menu.add_command(label=baslik, command=komut_olustur(baslik, secili_metin))

    menu.add_separator()
    menu.add_command(label="❌ İptal", command=lambda: None)

    try:
        x, y = pyautogui.position()
        menu.tk_popup(x, y)
    finally:
        menu.grab_release()


def on_press(key):
    global kisayol_basildi
    try:
        if key == KISAYOL_METIN and not kisayol_basildi:
            kisayol_basildi = True
            gui_queue.put((menu_goster, ()))
    except AttributeError:
        pass


def on_release(key):
    global kisayol_basildi
    try:
        if key == KISAYOL_METIN:
            kisayol_basildi = False
    except AttributeError:
        pass


if __name__ == "__main__":
    print("=" * 60)
    print("🤖 AI Asistan - Metin İşleme")
    print("=" * 60)
    aktif_text_model = get_available_text_model()
    print(f"📦 Metin İşleme (F8): {aktif_text_model}")
    print()
    print("🔧 Kullanım:")
    print("   F8 - Metin sec ve AI islemleri yap")
    print()
    print("⚠️ Programı kapatmak için bu pencereyi kapatın veya Ctrl+C yapın.")
    print("=" * 60)

    try:
        test_response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if test_response.status_code == 200:
            print("✅ Ollama bağlantısı başarılı!")
        else:
            print("⚠️ Ollama'ya bağlanılamadı, servisi kontrol edin!")
    except Exception:
        print("⚠️ Ollama çalışmıyor olabilir! 'ollama serve' ile başlatın.")

    print()

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    root = tk.Tk()
    root.withdraw()
    root.after(100, process_queue)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Kapatılıyor...")
