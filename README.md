# Sistem Peringatan Dini Banjir

Sistem Peringatan Dini Banjir berbasis web untuk memantau, melaporkan, dan memprediksi banjir secara real-time dengan teknologi AI.

##  Fitur Utama

###  Untuk Masyarakat
- **Lapor Banjir**: Form mudah untuk melaporkan kejadian banjir dengan upload foto
- **Peta Interaktif**: Visualisasi real-time lokasi banjir di peta
- **Notifikasi Status**: Update status laporan (pending, terverifikasi, selesai)
- **Geocoding Otomatis**: Konversi alamat ke koordinat GPS menggunakan OpenStreetMap

###  Untuk Petugas/Admin
- **Dashboard Real-time**: Monitor semua laporan masuk
- **Laporan Harian/Bulanan**: Statistik dan analisis data banjir
- **Prediksi AI**: 
  - Artificial Neural Network (ANN) untuk prediksi risiko banjir
  - Gumbel Distribution untuk analisis kejadian ekstrem
- **Export Data**: Sinkronisasi ke Google Sheets (optional)

###  Pemetaan & Geocoding
- Support **seluruh wilayah Indonesia** (34 provinsi, 514 kabupaten/kota)
- Smart address matching dengan OSM Nominatim
- Clustering markers untuk performa optimal
- Color-coded markers berdasarkan tinggi banjir

##  Quick Start

### Development (Local)

```bash
# 1. Clone repository
git clone https://github.com/username/flood-warning-system.git
cd flood-warning-system

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# atau
venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment variables
cp .env.example .env
# Edit .env sesuai kebutuhan

# 5. Initialize database
python models/database.py

# 6. Run application
python app.py
```

Akses aplikasi di: http://localhost:5000

### Production (Railway)

**Lihat panduan lengkap di [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**

#### Quick Deploy ke Railway:

1. **Fork/Clone repository ini**
2. **Connect ke Railway**:
   - Login ke https://railway.app
   - New Project → Deploy from GitHub
   - Pilih repository ini
3. **Set Environment Variables** (minimal):
   ```env
   SECRET_KEY=your-secret-key-here
   FLASK_DEBUG=False
   OSM_USER_AGENT=FloodWarningSystem/2.0 (your-email@example.com)
   ```
4. **Deploy!** Railway akan otomatis build dan deploy

##  Requirements

### Sistem Requirements
- Python 3.11+
- SQLite 3 (atau PostgreSQL untuk production)
- 512MB RAM minimum
- 1GB storage untuk database dan uploads

### Python Dependencies
```
Flask==2.3.3
gunicorn==21.2.0
requests==2.31.0
numpy==1.24.3
pandas==2.1.4
Pillow==10.1.0
python-dotenv==1.0.0
pytz==2023.3.post1
geopy==2.4.0
```

Lihat [requirements.txt](requirements.txt) untuk list lengkap.

## 🛠️ Teknologi

### Backend
- **Framework**: Flask 2.3.3
- **Database**: SQLite (development) / PostgreSQL (production)
- **Web Server**: Gunicorn
- **Geocoding**: OpenStreetMap Nominatim API

### Frontend
- **Template Engine**: Jinja2
- **UI Framework**: Bootstrap 5
- **Maps**: Leaflet.js dengan OpenStreetMap tiles
- **Charts**: Chart.js (untuk statistik)

### AI/ML
- **ANN**: Custom Artificial Neural Network untuk prediksi banjir
- **Gumbel Distribution**: Analisis kejadian ekstrem
- **Numpy & Pandas**: Data processing

### Integrasi
- **Google Sheets API**: Sync data (optional)
- **Google OAuth**: Service account untuk Sheets access

##  Struktur Project

```
flood-warning-system/
├── app.py                       # Main Flask application
├── config.py                    # Configuration settings
├── requirements.txt             # Python dependencies
├── runtime.txt                  # Python version
├── Procfile                     # Railway/Heroku deployment
├── railway.json                 # Railway configuration
├── nixpacks.toml               # Railway build config
│
├── models/                      # Database models
│   ├── __init__.py
│   ├── database.py              # Database initialization
│   ├── flood_report_model.py    # Flood report CRUD
│   └── google_sheets_model.py   # Google Sheets sync
│
├── controllers/                 # Business logic
│   ├── __init__.py
│   ├── flood_report_controller.py
│   └── realtime_data_controller.py
│
├── utils/                       # Utilities
│   ├── __init__.py
│   ├── helpers.py               # Helper functions & OSM geocoding
│   ├── model_ann.py             # ANN prediction model
│   └── gumbel_distribution.py   # Gumbel analysis
│
├── templates/                   # HTML templates
│   ├── layout.html              # Base template
│   ├── index.html               # Home page
│   ├── lapor_banjir.html        # Report form
│   ├── peta.html                # Interactive map
│   ├── harian.html              # Daily reports
│   ├── bulanan.html             # Monthly reports
│   ├── simulasi.html            # AI simulation
│   └── ...
│
├── static/                      # Static files
│   ├── style.css                # Custom styles
│   └── script.js                # Custom scripts
│
├── uploads/                     # User uploaded files
├── logs/                        # Application logs
└── backups/                     # Database backups
```

##  Configuration

### Environment Variables

Buat file `.env` dari template:
```bash
cp .env.example .env
```

**Minimal Configuration:**
```env
SECRET_KEY=your-secret-key-32-chars-minimum
FLASK_DEBUG=False
DATABASE_PATH=flood_system.db
GEOCODING_ENABLED=True
OSM_USER_AGENT=FloodWarningSystem/2.0 (your-email@example.com)
```

**Full Configuration:** Lihat [.env.example](.env.example)

### Google Sheets (Optional)

Untuk enable Google Sheets sync:

1. Create Google Cloud Project
2. Enable Google Sheets API
3. Create Service Account
4. Download credentials.json
5. Share spreadsheet dengan service account email
6. Set environment variables:
   ```env
   ENABLE_GOOGLE_SHEETS_SYNC=True
   SPREADSHEET_ID=your-spreadsheet-id
   ```

##  Database Schema

### Table: flood_reports

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| Timestamp | TEXT | Report timestamp |
| Alamat | TEXT | Flood location address |
| Tinggi Banjir | TEXT | Flood height (cm/meter) |
| Nama Pelapor | TEXT | Reporter name |
| No HP | TEXT | Reporter phone |
| IP Address | TEXT | Reporter IP |
| Photo URL | TEXT | Uploaded photo path |
| Status | TEXT | Report status (pending/terverifikasi/selesai) |
| latitude | REAL | GPS latitude |
| longitude | REAL | GPS longitude |
| is_geocoded | INTEGER | Geocoding status flag |
| geocode_confidence | TEXT | Geocoding confidence (HIGH/MEDIUM/LOW) |
| geocode_method | TEXT | Geocoding method (OSM/Manual) |
| geocoded_at | DATETIME | Geocoding timestamp |
| report_date | DATE | Report date |
| report_time | TIME | Report time |
| created_at | DATETIME | Record creation time |

##  Testing

### Run Tests
```bash
# Check database
python check_database.py

# Test geocoding
python batch_geocode.py --dry-run

# Test Google Sheets connection
python debug_sheets.py

# Clean duplicate data
python clean_duplicates.py
```

### Utility Scripts

- `check_database.py` - Verify database health
- `clean_duplicates.py` - Remove duplicate entries
- `batch_geocode.py` - Batch geocoding reports
- `view_geocode.py` - View geocoding results
- `debug_sheets.py` - Debug Google Sheets sync
- `fix_sync.py` - Sync database to Google Sheets
- `update_status.py` - Bulk update report status

##  Documentation

- [ Geocoding Guide](README_GEOCODING.md) - OSM geocoding for Indonesia
- [ Main README](README.md) - General system documentation

##  Troubleshooting

### Common Issues

**Build Failed on Railway:**
```
Error: Could not find requirements.txt
```
Solution: Ensure `requirements.txt` is in root directory

**Database Errors:**
```
Unable to open database file
```
Solution: Use Railway Volume for persistent storage

**Geocoding Timeout:**
```
OSM request timeout
```
Solution: Increase `GEOCODING_TIMEOUT` in environment variables

**Import Errors:**
```
ModuleNotFoundError: No module named 'models'
```
Solution: Ensure `__init__.py` files exist in all package folders

Lihat [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) untuk troubleshooting lengkap.

##  Security

- ✅ CSRF protection dengan form tokens
- ✅ File upload validation (type, size)
- ✅ SQL injection prevention (parameterized queries)
- ✅ XSS protection via template escaping
- ✅ Secure session management
- ✅ Environment variables untuk secrets
- ✅ Rate limiting untuk API endpoints

##  Roadmap

- [ ] PostgreSQL support untuk production database
- [ ] User authentication & authorization
- [ ] Email/SMS notifications untuk laporan banjir
- [ ] Mobile app (React Native)
- [ ] API documentation dengan Swagger
- [ ] Advanced AI models (LSTM, Prophet)
- [ ] Real-time WebSocket updates
- [ ] Multi-language support (ID, EN)
- [ ] Dark mode
- [ ] Export reports ke PDF/Excel

##  Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

##  License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

##  Authors

- **Tyara Wahyu Saputra** - *Initial work* - tyarawahyusaputra@gmail.com
- Phone: 085156959561

##  Acknowledgments

- OpenStreetMap Nominatim for geocoding service
- PythonAnywhere for hosting platform
- Flask community
- All contributors and testers

##  Support

- **Email**: tyarawahyusaputra@gmail.com
- **Phone**: 085156959561
- **Issues**: https://github.com/username/flood-warning-system/issues

---
