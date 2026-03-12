import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt

def hesapla():
    try:
        maliyet = float(maliyet_entry.get())
        fiyat = float(fiyat_entry.get())
        gunluk = int(satis_entry.get())

        kar = fiyat - maliyet
        onerilen_fiyat = maliyet * 1.5
        if fiyat > onerilen_fiyat:
            fiyat_oneri = "Fiyat zaten hedef kârın üzerinde."
        else:
            fiyat_oneri = f"{onerilen_fiyat:.2f} TL önerilir."
        basabas = maliyet / kar
        kar_orani = (kar / maliyet) * 100
        if kar_orani < 30:
            yorum = "⚠️ Bu ürünün kârı düşük. Fiyat artırılabilir."
        elif kar_orani < 60:
            yorum = "ℹ️ Orta seviyede kârlı bir ürün."
        else:
            yorum = "⭐ Çok kârlı. Menüde öne çıkarılabilir."
        gunluk_kar = kar * gunluk
        aylik_kar = gunluk_kar * 30
        gelir = fiyat * gunluk
        maliyet_toplam = maliyet * gunluk

        plt.figure()
        plt.bar(["Gelir", "Maliyet", "Kar"], [gelir, maliyet_toplam, gunluk_kar])
        plt.title("Gunluk Finans Analizi")
        plt.ylabel("TL")
        plt.show()
        sonuc = f"""
Porsiyon Kârı: {kar:.2f} TL
Kâr Oranı: %{kar_orani:.2f}
Günlük Kâr: {gunluk_kar:.2f} TL
Aylık Kâr: {aylik_kar:.2f} TL
Başabaş Satış: {basabas:.1f} porsiyon
Fiyat Önerisi: {fiyat_oneri}
Analiz: {yorum}
"""
        sonuc_label.config(text=sonuc)

    except:
        messagebox.showerror("Hata", "Lütfen tüm alanları doğru doldurun")

root = tk.Tk()
root.title("Menü Karlılık Analizi")
root.geometry("400x350")

tk.Label(root, text="Yemek Adı").pack()
yemek_entry = tk.Entry(root)
yemek_entry.pack()

tk.Label(root, text="Maliyet (TL)").pack()
maliyet_entry = tk.Entry(root)
maliyet_entry.pack()

tk.Label(root, text="Satış Fiyatı (TL)").pack()
fiyat_entry = tk.Entry(root)
fiyat_entry.pack()

tk.Label(root, text="Günlük Satış").pack()
satis_entry = tk.Entry(root)
satis_entry.pack()

tk.Button(root, text="Hesapla", command=hesapla).pack(pady=10)

sonuc_label = tk.Label(root, text="", fg="blue")
sonuc_label.pack()

root.mainloop()