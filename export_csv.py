import json
import os
import pandas as pd

CACHE_JSON = "rapor_cache.json"
OUTPUT_CSV = "tum_ogrenci_sql_puanlari.csv"
OUTPUT_EXCEL = "tum_ogrenci_sql_puanlari.xlsx"


def export_scores():
  print("=" * 60)
  print("🚀 ÖĞRENCİ SQL PUANLARI TERMİNAL CSV/EXCEL AKTARICI")
  print("=" * 60)

  if not os.path.exists(CACHE_JSON):
    print(f"❌ Hata: '{CACHE_JSON}' dosyası bulunamadı!")
    print(
        "Lütfen önce güncel cache dosyasının projede olduğundan emin olun"
        " (veya git pull yapın)."
    )
    return

  try:
    with open(CACHE_JSON, "r", encoding="utf-8") as f:
      cache_data = json.load(f)
  except Exception as e:
    print(f"❌ Cache dosyası okunurken hata oluştu: {e}")
    return

  results = []
  for student_name, data in cache_data.items():
    puan = data.get("puan", "Ödev Yok")
    results.append({"Öğrenci Adı": student_name, "Puan": puan})

  if not results:
    print("⚠️ Cache dosyası boş, aktarılacak öğrenci bulunamadı.")
    return

  df = pd.DataFrame(results)

  # CSV ve Excel olarak kaydet
  df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
  df.to_excel(OUTPUT_EXCEL, index=False)

  print(f"✅ Toplam {len(df)} öğrencinin puanı başarıyla dışa aktarıldı!")
  print(f"📄 CSV Dosyası   : {os.path.abspath(OUTPUT_CSV)}")
  print(f"📊 Excel Dosyası : {os.path.abspath(OUTPUT_EXCEL)}")
  print("=" * 60)


if __name__ == "__main__":
  export_scores()