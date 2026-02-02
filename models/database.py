import sqlite3
from datetime import datetime
import os
import sys
import json

class Database:
    def __init__(self, db_path='flood_system.db'):
        self.db_path = db_path
        self.connection = None
        
    def connect(self):
        """Create database connection"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            return self.connection
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            return None
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
    
    def execute_query(self, query, params=None):
        """Execute SQL query with proper connection handling"""
        conn = self.connect()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith("SELECT"):
                result = cursor.fetchall()
                return result
            else:
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"❌ Query execution error: {e}")
            conn.rollback()
            return None
        finally:
            self.close()
    
    def get_table_info(self, table_name):
        """Get table structure"""
        query = f"PRAGMA table_info({table_name})"
        result = self.execute_query(query)
        return result if result else []
    
    def table_exists(self, table_name):
        """Check if table exists"""
        query = """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
        """
        result = self.execute_query(query, (table_name,))
        return bool(result)
    
    def column_exists(self, table_name, column_name):
        """Check if column exists in table"""
        columns = self.get_table_info(table_name)
        column_names = [col['name'] for col in columns]
        return column_name in column_names
    
    def get_database_stats(self):
        """Get database statistics"""
        try:
            stats = {
                'path': self.db_path,
                'size': self.get_database_size(),
                'tables': self.get_table_list(),
                'row_counts': {}
            }
            
            # Get row counts for each table
            tables = stats['tables']
            for table in tables:
                query = f"SELECT COUNT(*) as count FROM {table}"
                result = self.execute_query(query)
                if result:
                    stats['row_counts'][table] = result[0]['count']
            
            return stats
        except Exception as e:
            print(f"❌ Error getting database stats: {e}")
            return {}
    
    def get_database_size(self):
        """Get database file size in MB"""
        try:
            if os.path.exists(self.db_path):
                size_bytes = os.path.getsize(self.db_path)
                return round(size_bytes / (1024 * 1024), 2)  # Convert to MB
            return 0
        except:
            return 0
    
    def get_table_list(self):
        """Get list of tables in database"""
        try:
            query = "SELECT name FROM sqlite_master WHERE type='table'"
            result = self.execute_query(query)
            return [row['name'] for row in result] if result else []
        except:
            return []
    
    def backup_database(self, backup_path=None):
        """Create database backup"""
        try:
            if not backup_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f"backups/flood_system_backup_{timestamp}.db"
            
            # Ensure backup directory exists
            os.makedirs(os.path.dirname(backup_path) if os.path.dirname(backup_path) else 'backups', exist_ok=True)
            
            import shutil
            shutil.copy2(self.db_path, backup_path)
            print(f"✅ Database backed up to: {backup_path}")
            return True, backup_path
        except Exception as e:
            print(f"❌ Database backup failed: {e}")
            return False, str(e)

def init_db():
    """Initialize database tables with all required columns"""
    db = Database()
    
    # ✅ FIXED: Create flood_reports table with geocoding columns included
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS flood_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        "Timestamp" TEXT,
        "Alamat" TEXT NOT NULL,
        "Tinggi Banjir" TEXT NOT NULL,
        "Nama Pelapor" TEXT NOT NULL,
        "No HP" TEXT,
        "IP Address" TEXT,
        "Photo URL" TEXT,
        "Status" TEXT DEFAULT 'pending',
        report_date DATE,
        report_time TIME,
        latitude REAL,
        longitude REAL,
        is_geocoded INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    '''
    
    result = db.execute_query(create_table_query)
    
    # Check if table was created successfully
    if db.table_exists('flood_reports'):
        print("✅ Table 'flood_reports' exists")
        
        # ✅ FIXED: Auto-migrate if columns are missing
        columns_to_check = ['latitude', 'longitude', 'is_geocoded']
        columns_added = False
        
        conn = db.connect()
        if conn:
            cursor = conn.cursor()
            try:
                for column in columns_to_check:
                    if not db.column_exists('flood_reports', column):
                        print(f"⚠️ Column '{column}' missing, adding...")
                        
                        if column == 'latitude' or column == 'longitude':
                            cursor.execute(f'ALTER TABLE flood_reports ADD COLUMN {column} REAL')
                        elif column == 'is_geocoded':
                            cursor.execute(f'ALTER TABLE flood_reports ADD COLUMN {column} INTEGER DEFAULT 0')
                        
                        conn.commit()
                        columns_added = True
                        print(f"✅ Column '{column}' added successfully")
                
                if columns_added:
                    print("✅ Database schema updated with geocoding columns")
                
            except Exception as e:
                print(f"❌ Error adding columns: {e}")
                conn.rollback()
            finally:
                db.close()
    
    # Create indexes for better performance
    indexes = [
        'CREATE INDEX IF NOT EXISTS idx_report_date ON flood_reports (report_date)',
        'CREATE INDEX IF NOT EXISTS idx_report_status ON flood_reports (Status)',
        'CREATE INDEX IF NOT EXISTS idx_ip_address ON flood_reports ("IP Address")',
        'CREATE INDEX IF NOT EXISTS idx_geocoded ON flood_reports (is_geocoded)',
        'CREATE INDEX IF NOT EXISTS idx_coordinates ON flood_reports (latitude, longitude)'
    ]
    
    for index_query in indexes:
        db.execute_query(index_query)
    
    # Check if table created successfully
    if db.table_exists('flood_reports'):
        print("✅ Database initialized successfully")
        columns = db.get_table_info('flood_reports')
        print(f"   Table 'flood_reports' has {len(columns)} columns")
        
        # Display column list
        print("   Columns:")
        for col in columns:
            col_name = col['name']
            col_type = col['type']
            print(f"      - {col_name} ({col_type})")
        
        # Display database stats
        stats = db.get_database_stats()
        print(f"   Database size: {stats.get('size', 0)} MB")
        print(f"   Tables: {', '.join(stats.get('tables', []))}")
        
        # Display row counts
        if stats.get('row_counts'):
            for table, count in stats['row_counts'].items():
                print(f"   {table}: {count} rows")
    else:
        print("❌ Failed to initialize database")
    
    # Create backup
    try:
        os.makedirs('backups', exist_ok=True)
        db.backup_database()
    except Exception as e:
        print(f"⚠️ Backup failed: {e}")
    
    return db

if __name__ == "__main__":
    print("="*60)
    print("🗄️  DATABASE INITIALIZATION")
    print("="*60)
    init_db()
    print("="*60)