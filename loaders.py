import os

def find_and_load_student_sql(student_name: str, data_dir: str = "./data") -> dict:
    """
    Mentörün girdiği öğrenci adını data/ klasöründe arar, 
    eşleşen .sql dosyasını bulur ve içeriğini okur.
    """
    if not os.path.exists(data_dir):
        return {"error": f"'{data_dir}' klasörü bulunamadı."}

    # "Ahmet Yılmaz" -> "ahmet_yilmaz" formatına çeviriyoruz
    search_term = student_name.strip().lower().replace(" ", "_")

    files = os.listdir(data_dir)
    matched_file = None
    for file in files:
        if file.endswith(".sql") and search_term in file.lower():
            matched_file = file
            break
    
    if not matched_file:
        return {"error": f"'{student_name}' adlı öğrenciye ait bir .sql dosyası bulunamadı."}

    file_path = os.path.join(data_dir, matched_file)
    
    # Düz metin olarak SQL dosyasını okuyoruz
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            sql_content = f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1") as f:
            sql_content = f.read()

    return {
        "dosya_adi": matched_file,
        "sql_kodu": sql_content
    }