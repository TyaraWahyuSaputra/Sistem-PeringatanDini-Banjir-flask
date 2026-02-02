import sqlite3
from datetime import datetime

def show_reports():
    """Tampilkan semua laporan"""
    conn = sqlite3.connect('flood_system.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, substr("Alamat", 1, 30) as alamat, "Status", "Timestamp"
        FROM flood_reports
        ORDER BY id DESC
        LIMIT 20
    ''')
    
    print("\n" + "="*80)
    print("LAPORAN BANJIR (20 Terbaru)")
    print("="*80)
    print(f"{'ID':<5} {'Alamat':<32} {'Status':<15} {'Timestamp'}")
    print("-"*80)
    
    for row in cursor.fetchall():
        print(f"{row[0]:<5} {row[1]:<32} {row[2]:<15} {row[3]}")
    
    conn.close()

def show_status_distribution():
    """Tampilkan distribusi status"""
    conn = sqlite3.connect('flood_system.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT "Status", COUNT(*) as jumlah
        FROM flood_reports
        GROUP BY "Status"
        ORDER BY jumlah DESC
    ''')
    
    print("\n" + "="*80)
    print("DISTRIBUSI STATUS")
    print("="*80)
    
    for row in cursor.fetchall():
        print(f"{row[0]:<15}: {row[1]} laporan")
    
    conn.close()

def update_status(report_id, new_status):
    """Update status laporan berdasarkan ID"""
    valid_statuses = ['pending', 'terverifikasi', 'selesai']
    
    if new_status not in valid_statuses:
        print(f"❌ Status tidak valid! Pilih: {', '.join(valid_statuses)}")
        return False
    
    conn = sqlite3.connect('flood_system.db')
    cursor = conn.cursor()
    
    # Cek apakah laporan ada
    cursor.execute('SELECT id, "Alamat" FROM flood_reports WHERE id = ?', (report_id,))
    result = cursor.fetchone()
    
    if not result:
        print(f"❌ Laporan dengan ID {report_id} tidak ditemukan!")
        conn.close()
        return False
    
    alamat = result[1]
    
    # Update status
    cursor.execute('''
        UPDATE flood_reports 
        SET "Status" = ? 
        WHERE id = ?
    ''', (new_status, report_id))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Status laporan #{report_id} ({alamat[:30]}) berhasil diubah menjadi '{new_status}'")
    return True

def update_bulk_by_date(before_date, new_status):
    """Update status banyak laporan sekaligus berdasarkan tanggal"""
    valid_statuses = ['pending', 'terverifikasi', 'selesai']
    
    if new_status not in valid_statuses:
        print(f"❌ Status tidak valid! Pilih: {', '.join(valid_statuses)}")
        return 0
    
    conn = sqlite3.connect('flood_system.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE flood_reports 
        SET "Status" = ? 
        WHERE report_date < ?
    ''', (new_status, before_date))
    
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"✅ Berhasil update {affected} laporan menjadi '{new_status}'")
    return affected

def update_geocoded_reports(new_status):
    """Update status laporan yang sudah di-geocode"""
    valid_statuses = ['pending', 'terverifikasi', 'selesai']
    
    if new_status not in valid_statuses:
        print(f"❌ Status tidak valid! Pilih: {', '.join(valid_statuses)}")
        return 0
    
    conn = sqlite3.connect('flood_system.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE flood_reports 
        SET "Status" = ? 
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        AND "Status" = 'pending'
    ''', (new_status,))
    
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"✅ Berhasil update {affected} laporan yang sudah di-geocode menjadi '{new_status}'")
    return affected

def update_bulk_by_ids(report_ids, new_status):
    """Update status beberapa laporan sekaligus berdasarkan ID"""
    valid_statuses = ['pending', 'terverifikasi', 'selesai']
    
    if new_status not in valid_statuses:
        print(f"❌ Status tidak valid! Pilih: {', '.join(valid_statuses)}")
        return 0
    
    conn = sqlite3.connect('flood_system.db')
    cursor = conn.cursor()
    
    placeholders = ','.join('?' * len(report_ids))
    query = f'UPDATE flood_reports SET "Status" = ? WHERE id IN ({placeholders})'
    
    cursor.execute(query, [new_status] + report_ids)
    
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"✅ Berhasil update {affected} laporan menjadi '{new_status}'")
    return affected

def backup_database():
    """Buat backup database"""
    import shutil
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'flood_system_backup_{timestamp}.db'
    
    try:
        shutil.copy2('flood_system.db', backup_name)
        print(f"✅ Backup berhasil dibuat: {backup_name}")
        return True
    except Exception as e:
        print(f"❌ Backup gagal: {e}")
        return False

# ==================== MENU INTERAKTIF ====================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🔧 TOOL UPDATE STATUS LAPORAN BANJIR")
    print("="*80)
    
    while True:
        print("\n" + "-"*80)
        print("MENU UTAMA:")
        print("-"*80)
        print("1. Tampilkan semua laporan (20 terbaru)")
        print("2. Tampilkan distribusi status")
        print("3. Update status 1 laporan (by ID)")
        print("4. Update status beberapa laporan (by IDs)")
        print("5. Update semua laporan lama (by date)")
        print("6. Update semua laporan yang sudah di-geocode")
        print("7. Backup database")
        print("8. Keluar")
        print("-"*80)
        
        choice = input("\nMasukkan pilihan (1-8): ").strip()
        
        if choice == '1':
            show_reports()
        
        elif choice == '2':
            show_status_distribution()
        
        elif choice == '3':
            show_reports()
            report_id = input("\nMasukkan ID laporan yang ingin diubah: ").strip()
            print("\nStatus yang tersedia: pending, terverifikasi, selesai")
            new_status = input("Masukkan status baru: ").strip().lower()
            
            try:
                update_status(int(report_id), new_status)
            except ValueError:
                print("❌ ID harus berupa angka!")
        
        elif choice == '4':
            show_reports()
            ids_input = input("\nMasukkan ID laporan (pisahkan dengan koma, contoh: 146,147,148): ").strip()
            print("\nStatus yang tersedia: pending, terverifikasi, selesai")
            new_status = input("Masukkan status baru: ").strip().lower()
            
            try:
                report_ids = [int(id.strip()) for id in ids_input.split(',')]
                confirm = input(f"\n⚠️ Yakin update {len(report_ids)} laporan? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    update_bulk_by_ids(report_ids, new_status)
            except ValueError:
                print("❌ Format ID tidak valid! Gunakan angka dipisah koma.")
        
        elif choice == '5':
            before_date = input("\nMasukkan tanggal (YYYY-MM-DD), laporan sebelum tanggal ini akan diubah: ").strip()
            print("\nStatus yang tersedia: pending, terverifikasi, selesai")
            new_status = input("Masukkan status baru: ").strip().lower()
            
            confirm = input(f"\n⚠️ Yakin update SEMUA laporan sebelum {before_date}? (yes/no): ").strip().lower()
            if confirm == 'yes':
                update_bulk_by_date(before_date, new_status)
        
        elif choice == '6':
            print("\nStatus yang tersedia: pending, terverifikasi, selesai")
            new_status = input("Masukkan status baru untuk laporan yang sudah di-geocode: ").strip().lower()
            
            confirm = input(f"\n⚠️ Yakin update SEMUA laporan yang sudah punya koordinat? (yes/no): ").strip().lower()
            if confirm == 'yes':
                update_geocoded_reports(new_status)
        
        elif choice == '7':
            backup_database()
        
        elif choice == '8':
            print("\n" + "="*80)
            print("👋 Terima kasih telah menggunakan tool ini!")
            print("="*80)
            break
        
        else:
            print("❌ Pilihan tidak valid! Pilih 1-8.")