import os
import time
import pandas as pd
from loaders import (
    get_oauth_drive_service,
    get_sql_file_from_student_folder,
    list_student_folders,
)
from raghelper import evaluate_student_sql


def main():
  print("🚀 Google Drive bağlantısı kuruluyor...")
  service = get_oauth_drive_service()

  if not service:
    print(
        "❌ Google Drive'a bağlanılamadı. Lütfen yetkilendirmeyi kontrol edin."
    )
    return

  # 1. Adım: Daha önce oluşturulmuş bir rapor var mı kontrol et (Akıllı Hafıza)
  eski_sonuclar_dict = {}
  output_excel = "tum_ogrenci_sql_puanlari.xlsx"

  if os.path.exists(output_excel):
    print(
        "📂 Önceki tarama sonuçları bulundu. Akıllı önbellek yükleniyor...",
        end=" ",
    )
    try:
      df_eski = pd.read_excel(output_excel)
      # Öğrenci adını anahtar, rapor ve dosya bilgilerini değer olarak sözlüğe atıyoruz
      for _, row in df_eski.iterrows():
        eski_sonuclar_dict[row["Ogrenci_Adi"]] = {
            "Dosya_Adi": row.get("Dosya_Adi", ""),
            "Degerlendirme_Raporu": row.get("Degerlendirme_Raporu", ""),
        }
      print(f"({len(eski_sonuclar_dict)} öğrenci hafızadan yüklendi)")
    except Exception as e:
      print(f"⚠️ Eski dosya okunamadı, sıfırdan başlanacak: {e}")

  print("📂 Google Drive'dan güncel öğrenci klasörleri listeleniyor...")
  student_folders = list_student_folders()
  toplam_ogrenci = len(student_folders)

  print(
      f"📊 Toplam {toplam_ogrenci} öğrenci tarandı. Akıllı kontrol"
      " başlatılıyor...\n"
  )

  sonuclar = []
  yeni_veya_guncellenen_sayisi = 0
  hafidadan_gelen_sayisi = 0

  for index, (ogrenci_adi, klasor_id) in enumerate(student_folders.items()):
    print(f"[{index+1}/{toplam_ogrenci}] Kontrol ediliyor: {ogrenci_adi}...", end=" ")

    try:
      # Drive'dan SQL dosyasını ve dosya meta verilerini (veya içeriğini) çek
      sql_kodu, file_name = get_sql_file_from_student_folder(
          service, klasor_id
      )

      # AKILLI KONTROL MANTIĞI:
      # Eğer öğrenci daha önce taranmışsa VE dosya adı aynı kalmışsa (ekstra hız ve token tasarrufu için)
      # Not: İstersen buraya dosya güncelleme tarihini de entegre edebiliriz.
      if (
          ogrenci_adi in eski_sonuclar_dict
          and eski_sonuclar_dict[ogrenci_adi]["Dosya_Adi"] == file_name
          and file_name != "Dosya Bulunamadı"
      ):
        # Yapay zekaya tekrar gönderme, eski sonucunu koru!
        print("⚡ Hafızadan alındı (Token harcanmadı)")
        sonuclar.append({
            "Ogrenci_Adi": ogrenci_adi,
            "Dosya_Adi": file_name,
            "Degerlendirme_Raporu": eski_sonuclar_dict[ogrenci_adi][
                "Degerlendirme_Raporu"
            ],
        })
        hafidadan_gelen_sayisi += 1
      else:
        # Yeni ödev yüklemiş veya ilk kez taranıyor -> GPT-4o'ya gönder!
        if sql_kodu:
          print("🤖 Yeni/Güncel ödev! GPT-4o ile inceleniyor...", end=" ")
          report = evaluate_student_sql(sql_kodu)
          print(f"✅ Başarılı ({file_name})")

          sonuclar.append({
              "Ogrenci_Adi": ogrenci_adi,
              "Dosya_Adi": file_name,
              "Degerlendirme_Raporu": report,
          })
          yeni_veya_guncellenen_sayisi += 1
          # API sınırlarını korumak için sadece yapay zekaya gittiğinde bekle
          time.sleep(1)
        else:
          print(f"⚠️ Dosya Bulunamadı ({file_name})")
          sonuclar.append({
              "Ogrenci_Adi": ogrenci_adi,
              "Dosya_Adi": "Dosya Bulunamadı",
              "Degerlendirme_Raporu": "Ödev yüklenmemiş.",
          })

    except Exception as e:
      print(f"❌ Hata: {e}")
      sonuclar.append({
          "Ogrenci_Adi": ogrenci_adi,
          "Dosya_Adi": "Hata",
          "Degerlendirme_Raporu": str(e),
      })

  # DataFrame'e çevir ve çıktıları kaydet
  df = pd.DataFrame(sonuclar)

  csv_adi = "tum_ogrenci_sql_puanlari.csv"

  df.to_excel(output_excel, index=False, sheet_name="Puanlar")
  df.to_csv(csv_adi, index=False, encoding="utf-8-sig")

  print("\n" + "=" * 50)
  print("🎉 AKILLI TARAMA TAMAMLANDI!")
  print(f"⚡ Hafızadan Kullanılan (Token Harcanmayan): {hafidadan_gelen_sayisi}")
  print(f"🤖 Yeni Puanlanan (GPT-4o Çağrılan): {yeni_veya_guncellenen_sayisi}")
  print(f"📊 Güncel Excel Raporu: {output_excel}")
  print("=" * 50)


if __name__ == "__main__":
  main()