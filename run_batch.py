import os
import pandas as pd

output_csv = "tum_ogrenci_sql_puanlari.csv"
output_excel = "tum_ogrenci_sql_puanlari.xlsx"


def main():
  print("=" * 60)
  print("🚀 MENTOR COCKPIT - ÖĞRENCİ SQL PUANLARI RAPOR GÖRÜNTÜLEYİCİ")
  print("=" * 60)

  if os.path.exists(output_csv):
    print(f"\n📂 Güncel rapor dosyası okunuyor: {output_csv}\n")
    df = pd.read_csv(output_csv)

    # Terminalde özet bilgileri ve öğrenci listesini göster
    print(f"📊 Toplam Öğrenci Sayısı: {len(df)}")
    print("-" * 60)

    for idx, row in df.iterrows():
      # Yeni CSV yapısına göre sadece Ad ve Puan basılıyor
      print(
          f"{idx+1}. Öğrenci: {row['Öğrenci Adı']} | Puan / Durum:"
          f" {row['Puan']}"
      )

    print("-" * 60)
    print("\n✅ Rapor başarıyla terminale yazdırıldı!")
    print(f"📁 CSV Yolu: {os.path.abspath(output_csv)}")
    if os.path.exists(output_excel):
      print(f"📁 Excel Yolu: {os.path.abspath(output_excel)}")
  else:
    print("\n⚠️ Henüz oluşturulmuş toplu bir rapor bulunamadı!")
    print(
        "Lütfen önce Streamlit arayüzünü açıp yönetici şifresiyle 'Tüm Sınıfı"
        " Tara ve Raporu Güncelle' butonuna basın."
    )


if __name__ == "__main__":
  main()