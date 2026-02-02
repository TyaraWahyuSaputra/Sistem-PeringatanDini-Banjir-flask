# Sistem Pemetaan Laporan Banjir dengan OSM Geocoding

## 📋 Deskripsi Sistem

Sistem ini mengonversi alamat administratif Indonesia (kelurahan, kecamatan, kabupaten/kota, provinsi) dari **seluruh wilayah Indonesia** menjadi koordinat geografis menggunakan OpenStreetMap (OSM) Nominatim Geocoding API, kemudian menampilkan titik-titik banjir di peta interaktif dengan warna berbeda berdasarkan ketinggian air.

### 🗺️ Coverage Area
- ✅ 34 Provinsi Indonesia  
- ✅ 514 Kabupaten/Kota
- ✅ 7.094 Kecamatan
- ✅ 83.820 Kelurahan/Desa

**Dari Sabang sampai Merauke, dari Miangas sampai Rote!**

## ✨ Fitur Utama

### 1. **Geocoding Otomatis**
- Mengkonversi alamat teks menjadi koordinat GPS (latitude, longitude)
- Support format alamat administratif Indonesia (seluruh Indonesia)
- Validasi hasil geocoding (harus dalam batas Indonesia)
- Confidence scoring (HIGH, MEDIUM, LOW)
- Smart matching untuk semua provinsi, kabupaten, kecamatan, dan kelurahan di Indonesia

### 2. **Peta Interaktif**
- Marker berwarna berdasarkan ketinggian banjir:
  - 🟢 **Hijau**: < 25 cm (Rendah)
  - 🟡 **Kuning**: 25-50 cm (Menengah)
  - 🔴 **Merah**: 50-100 cm (Tinggi)
  - 🟣 **Ungu**: > 100 cm (Ekstrem)
- Clustering untuk performa optimal
- Popup detail untuk setiap laporan

### 3. **Notifikasi Laporan Gagal**
- Menampilkan peringatan untuk laporan yang belum ter-geocode
- List detail alamat yang gagal
- Saran untuk perbaikan

## 🚀 Cara Penggunaan

### 1. **Menjalankan Geocoding**

#### A. Test dengan Dry Run (Preview)
```bash
python geocode_reports.py --dry-run
```
Ini akan menampilkan preview tanpa mengubah database.

#### B. Geocoding 5 Laporan Pertama (Testing)
```bash
python geocode_reports.py --limit 5
```

#### C. Geocoding Semua Laporan
```bash
python geocode_reports.py
```

#### D. Geocoding dengan Konfirmasi Manual
```bash
python geocode_reports.py --interactive
```
Sistem akan meminta konfirmasi untuk setiap hasil geocoding.

#### E. Geocoding Laporan Tertentu
```bash
python geocode_reports.py --ids 0,146,147,148
```

#### F. Re-geocode Semua (Force Update)
```bash
python geocode_reports.py --force
```

### 2. **Melihat Hasil Geocoding**

```bash
# Lihat statistik
python view_geocode.py --stats

# Lihat laporan yang ter-geocode
python view_geocode.py

# Lihat laporan yang gagal
python view_geocode.py --failed

# Generate peta HTML
python view_geocode.py --map
```

### 3. **Melihat Peta di Web**

Jalankan aplikasi Flask:
```bash
python app.py
```

Kemudian buka browser dan akses:
```
http://localhost:5000/peta
```

## 📊 Struktur Database

Tabel `flood_reports` memiliki kolom geocoding:

| Kolom | Tipe | Deskripsi |
|-------|------|-----------|
| `latitude` | REAL | Koordinat lintang |
| `longitude` | REAL | Koordinat bujur |
| `geocode_confidence` | TEXT | Tingkat kepercayaan (HIGH/MEDIUM/LOW) |
| `geocode_method` | TEXT | Metode geocoding (OSM/Manual) |
| `geocoded_at` | DATETIME | Timestamp geocoding |

## 🔧 Konfigurasi

File: `config.py`

```python
# OpenStreetMap Configuration
OSM_USER_AGENT = "FloodWarningSystem/2.0 (email@example.com)"
OSM_RATE_LIMIT_DELAY = 1.1  # detik (sesuai policy OSM)
GEOCODING_ENABLED = True
```

## 📍 Format Alamat yang Disarankan

Untuk hasil geocoding terbaik, gunakan format:

### ✅ Format Bagus:
```
# Jawa Tengah
mangkuyudan, kartasura, sukoharjo
desa ampel, boyolali
malangjiwan, colomadu, karanganyar

# Jawa Barat
cibaduyut, bandung
cianjur, jawa barat

# Jawa Timur
surabaya, jawa timur
malang, jawa timur

# Sulawesi
beteleme, palu, sulawesi tengah
makassar, sulawesi selatan

# Sumatra
medan, sumatra utara
palembang, sumatra selatan

# Kalimantan
balikpapan, kalimantan timur
banjarmasin, kalimantan selatan
```

### ⚠️ Format Kurang Bagus:
```
mangkuyudan  (terlalu umum)
jl raya  (tidak spesifik)
rumah saya  (tidak valid)
```

### 💡 Tips:
1. Sertakan minimal: Kelurahan/Desa + Kecamatan + Kabupaten/Kota + Provinsi
2. Hindari prefiks: "Desa", "Kecamatan", "Kabupaten", "Provinsi" (akan dihapus otomatis)
3. Untuk daerah yang kurang dikenal, sertakan provinsi: "Beteleme, Palu, Sulawesi Tengah"
4. Gunakan nama resmi daerah (sesuai yang ada di peta)
5. Untuk kota besar, nama kota saja sudah cukup: "Jakarta", "Surabaya", "Medan"

## 🎯 Cara Kerja Geocoding

1. **Cleaning Address**: Menghapus prefiks (desa, kecamatan, kabupaten, provinsi)
2. **OSM Search**: Mencari 5 hasil teratas dari OpenStreetMap
3. **Smart Matching**: Memilih hasil terbaik berdasarkan:
   - Lokasi di Indonesia (+30 poin)
   - Kecocokan kata kunci dari alamat (+20 poin per kata)
   - Bonus untuk multiple word match (+15-30 poin)
   - Spesifisitas lokasi:
     - Desa/Dusun: +40 poin
     - Kelurahan: +35 poin
     - Kecamatan: +30 poin
     - Kota: +20 poin
     - Kabupaten: +15 poin
     - Provinsi: +10 poin
   - Exact match di komponen alamat (+25-35 poin)
   - OSM Importance Score (×25)
4. **Validation**: Memastikan koordinat dalam batas Indonesia
5. **Confidence Scoring**:
   - HIGH: Alamat spesifik (nomor rumah, bangunan)
   - MEDIUM: Jalan, desa, kelurahan
   - LOW: Kota, provinsi

## 🗺️ Visualisasi Peta

### Komponen Peta:
1. **Base Map**: OpenStreetMap tiles
2. **Marker Clustering**: Otomatis mengelompokkan marker yang berdekatan
3. **Color Coding**: Berdasarkan ketinggian banjir
4. **Popup**: Informasi detail saat marker diklik
5. **Failed Geocode Notice**: Panel peringatan untuk laporan tanpa koordinat

### Interaksi:
- **Klik Marker**: Lihat detail laporan
- **Zoom**: Scroll mouse atau +/- button
- **Pan**: Drag peta
- **Cluster Click**: Zoom ke area cluster

## 🛠️ Troubleshooting

### Problem: "Koneksi error - periksa internet"
**Solusi**: 
- Pastikan koneksi internet aktif
- OSM Nominatim memerlukan internet
- Coba lagi setelah beberapa saat

### Problem: "Alamat tidak ditemukan di OpenStreetMap"
**Solusi**:
- Periksa typo di alamat
- Coba format yang lebih spesifik
- Tambahkan kota/kabupaten
- Gunakan mode `--interactive` untuk review manual

### Problem: "Rate limit exceeded"
**Solusi**:
- OSM membatasi 1 request per detik
- Script sudah mengatur delay 1.1 detik
- Untuk batch besar, proses akan memakan waktu
- Jangan interrupt proses

### Problem: "Koordinat di luar Indonesia"
**Solusi**:
- Alamat mungkin tidak valid
- OSM menemukan tempat dengan nama sama di negara lain
- Tambahkan ", Indonesia" di akhir alamat
- Review hasil dengan mode `--interactive`

## 📈 Best Practices

### 1. **Test Dulu**
```bash
# Selalu test dengan dry-run
python geocode_reports.py --dry-run

# Atau test limit kecil
python geocode_reports.py --limit 5
```

### 2. **Backup Database**
Script otomatis membuat backup, tapi bisa manual:
```bash
cp flood_system.db flood_system_backup.db
```

### 3. **Review Hasil**
```bash
# Cek statistik
python view_geocode.py --stats

# Cek yang gagal
python view_geocode.py --failed
```

### 4. **Iterative Approach**
1. Geocode batch kecil (--limit 10)
2. Review hasil
3. Perbaiki alamat yang gagal
4. Geocode sisanya

## 📞 Support

Untuk pertanyaan atau issues:
- Email: tyarawahyusaputra@gmail.com
- Check logs di console
- Lihat backup database di folder `backups/`

## 📝 Changelog

### v2.1 (Current)
- ✅ **NATIONWIDE SUPPORT**: Sistem sekarang mendukung seluruh Indonesia
- ✅ Smart address matching untuk 34 provinsi, 514 kabupaten/kota
- ✅ Prioritas berbasis spesifisitas lokasi (desa > kelurahan > kecamatan > kota)
- ✅ Multi-word matching dengan bonus scoring
- ✅ Exact match detection untuk komponen alamat
- ✅ Enhanced OSM importance weighting

### v2.0
- ✅ OSM Geocoding support
- ✅ Smart address matching untuk Indonesia
- ✅ Failed geocode notification
- ✅ Color-coded markers berdasarkan ketinggian banjir
- ✅ Interactive preview mode
- ✅ Automatic backup system

### v1.0
- Basic manual coordinate input
- Simple map display

## 🔜 Roadmap

- [ ] Manual coordinate correction UI
- [ ] Batch address validation
- [ ] Export to GeoJSON
- [ ] Historical flood overlay
- [ ] Mobile app support

---
