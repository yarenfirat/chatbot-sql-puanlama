-- 1. Soru: Tüm departmanların adını ve lokasyonunu listeleyen sorguyu yazınız.
SELECT DepartmanAdi, Lokasyon 
FROM Departman;

-- 2. Soru: İstanbul lokasyonunda bulunan departmanları listeleyen sorguyu yazınız.
SELECT * 
FROM Departman 
WHERE Sehir = 'İstanbul';

-- 3. Soru: Maaşı 60.000 TL'den büyük olan personelin adını ve maaşını listeleyen sorguyu yazınız.
SELECT AdSoyad, Maas 
FROM Personel 
WHERE Maas > 60000;

-- 4. Soru: Her personelin adını ve çalıştığı departman adını listeleyen sorguyu yazınız.
SELECT p.AdSoyad, d.DepartmanAdi 
FROM Personel p
JOIN Departman d ON p.DepartmanID = d.DepartmanID;

-- 5. Soru: Personellerin adını ve katıldıkları eğitimlerin adını listeleyen sorguyu yazınız.
SELECT p.AdSoyad, e.EgitimAdi 
FROM Personel p
JOIN EgitimKatilim e ON p.DepartmanID = e.PersonelID;

-- 6. Soru: Her bir departmanda toplam kaç personel olduğunu gösteren sorguyu yazınız.
SELECT DepartmanID, COUNT(*) AS PersonelSayisi 
FROM Personel 
GROUP BY DepartmanID;

-- 7. Soru: Departman bazında ortalama personel maaşlarını hesaplayan sorguyu yazınız.
SELECT DepartmanID, AVG(Maas) AS OrtalamaMaas 
FROM Personel;

-- 8. Soru: İstanbul lokasyonundaki departmanlarda çalışan ve "SQL Temelleri" eğitimine katılan personelin adını listeleyiniz.
SELECT p.AdSoyad 
FROM Personel p
JOIN Departman d ON p.DepartmanID = d.DepartmanID
JOIN EgitimKatilim e ON p.PersonelID = e.PersonelID
WHERE d.Lokasyon = 'İstanbul' AND e.EgitimAdi = 'SQL Temelleri';

-- 9. Soru: Maaşı 50.000 TL'den fazla olan personelin adını ve unvanını listeleyen sorguyu yazınız.
SELECT AdSoyad, Unvan 
FROM Personel 
WHERE Maas > 50000;

-- 10. Soru: Şirket ortalama maaşının üzerinde maaş alan personelleri listeleyen sorguyu yazınız.
SELECT AdSoyad, Maas 
FROM Personel 
WHERE Maas > (SELECT AVG(Maas) FROM Personel);
