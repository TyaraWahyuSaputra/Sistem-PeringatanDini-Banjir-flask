import sqlite3
from datetime import datetime
import os
import sys
import json

class Database:
    def __init__(self, db_path=None):
        """
        Initialize database with absolute path
        
        CRITICAL: Always use absolute path for consistency between local and production
        """
        if db_path is None:
            # Get absolute path to database from config
            from config import Config
            self.db_path = Config.DATABASE_PATH
        else:
            # Ensure provided path is absolute
            self.db_path = os.path.abspath(db_path)
        
        self.connection = None
        print(f"📊 Database initialized: {self.db_path}")
        
    def connect(self):
        """Create database connection"""
        try:
            # Ensure database directory exists
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            self.connection = sqlite3.connect(self.db_path, timeout=30.0)
            self.connection.row_factory = sqlite3.Row
            
            # Enable WAL mode for better concurrency (safe for PythonAnywhere)
            self.connection.execute('PRAGMA journal_mode=WAL')
            
            return self.connection
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def close(self):
        """Close database connection"""
        if self.connection:
            try:
                self.connection.close()
            except Exception as e:
                print(f"⚠️ Error closing connection: {e}")
    
    def execute_query(self, query, params=None):
        """Execute SQL query with proper connection handling"""
        conn = self.connect()
        if not conn:
            print(f"❌ Failed to connect to database")
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
        except sqlite3.Error as e:
            print(f"❌ Database error: {e}")
            print(f"   Query: {query[:100]}...")
            if params:
                print(f"   Params: {params}")
            conn.rollback()
            import traceback
            traceback.print_exc()
            return None
        except Exception as e:
            print(f"❌ Query execution error: {e}")
            import traceback
            traceback.print_exc()
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
        if not columns:
            return False
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
        except Exception as e:
            print(f"⚠️ Error getting database size: {e}")
            return 0
    
    def get_table_list(self):
        """Get list of tables in database"""
        try:
            query = "SELECT name FROM sqlite_master WHERE type='table'"
            result = self.execute_query(query)
            return [row['name'] for row in result] if result else []
        except Exception as e:
            print(f"⚠️ Error getting table list: {e}")
            return []
    
    def backup_database(self, backup_path=None):
        """Create database backup"""
        try:
            if not backup_path:
                # Create backups directory
                from config import Config
                backup_dir = Config.BACKUP_DIR
                os.makedirs(backup_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = os.path.join(backup_dir, f"flood_system_backup_{timestamp}.db")
            
            # Ensure backup directory exists
            backup_dir = os.path.dirname(backup_path)
            if backup_dir and not os.path.exists(backup_dir):
                os.makedirs(backup_dir, exist_ok=True)
            
            import shutil
            shutil.copy2(self.db_path, backup_path)
            print(f"✅ Database backed up to: {backup_path}")
            return True, backup_path
        except Exception as e:
            print(f"❌ Database backup failed: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)


def init_db():
    """
    Initialize database tables with all required columns
    
    CRITICAL: This function creates the database schema
    Must work identically in local and PythonAnywhere environments
    """
    db = Database()
    
    print("\n" + "="*70)
    print("📋 INITIALIZING DATABASE")
    print("="*70)
    print(f"Database path: {db.db_path}")
    print(f"Absolute path: {os.path.abspath(db.db_path)}")
    
    # Create flood_reports table with ALL required columns
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS flood_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        "Timestamp" TEXT NOT NULL,
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
        geocode_confidence TEXT,
        geocode_method TEXT,
        geocoded_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    '''
    
    print("\n📝 Creating table...")
    result = db.execute_query(create_table_query)
    
    # Check if table was created successfully
    if db.table_exists('flood_reports'):
        print("✅ Table 'flood_reports' exists")
        
        # Auto-migrate missing columns
        required_columns = {
            'latitude': 'REAL',
            'longitude': 'REAL',
            'is_geocoded': 'INTEGER DEFAULT 0',
            'geocode_confidence': 'TEXT',
            'geocode_method': 'TEXT',
            'geocoded_at': 'DATETIME'
        }
        
        columns_added = False
        conn = db.connect()
        
        if conn:
            cursor = conn.cursor()
            try:
                for column_name, column_type in required_columns.items():
                    if not db.column_exists('flood_reports', column_name):
                        print(f"⚠️  Column '{column_name}' missing, adding...")
                        
                        try:
                            cursor.execute(f'ALTER TABLE flood_reports ADD COLUMN {column_name} {column_type}')
                            conn.commit()
                            columns_added = True
                            print(f"✅ Column '{column_name}' added successfully")
                        except sqlite3.OperationalError as e:
                            if "duplicate column name" in str(e).lower():
                                print(f"ℹ️  Column '{column_name}' already exists")
                            else:
                                print(f"❌ Error adding column '{column_name}': {e}")
                
                if columns_added:
                    print("✅ Database schema updated with new columns")
                
            except Exception as e:
                print(f"❌ Error during migration: {e}")
                import traceback
                traceback.print_exc()
                conn.rollback()
            finally:
                db.close()
    else:
        print("❌ Failed to create table")
        return db
    
    # Create indexes for better performance
    indexes = [
        'CREATE INDEX IF NOT EXISTS idx_report_date ON flood_reports (report_date)',
        'CREATE INDEX IF NOT EXISTS idx_report_status ON flood_reports ("Status")',
        'CREATE INDEX IF NOT EXISTS idx_ip_address ON flood_reports ("IP Address")',
        'CREATE INDEX IF NOT EXISTS idx_geocoded ON flood_reports (is_geocoded)',
        'CREATE INDEX IF NOT EXISTS idx_coordinates ON flood_reports (latitude, longitude)',
        'CREATE INDEX IF NOT EXISTS idx_timestamp ON flood_reports ("Timestamp")'
    ]
    
    print("\n📇 Creating indexes...")
    for index_query in indexes:
        db.execute_query(index_query)
    print("✅ Indexes created")
    
    # Display table information
    if db.table_exists('flood_reports'):
        columns = db.get_table_info('flood_reports')
        print(f"\n✅ Table 'flood_reports' has {len(columns)} columns:")
        
        for col in columns:
            col_name = col['name']
            col_type = col['type']
            col_notnull = " NOT NULL" if col['notnull'] else ""
            col_default = f" DEFAULT {col['dflt_value']}" if col['dflt_value'] else ""
            print(f"   - {col_name} ({col_type}){col_notnull}{col_default}")
        
        # Display database stats
        stats = db.get_database_stats()
        print(f"\n📊 Database Statistics:")
        print(f"   Size: {stats.get('size', 0)} MB")
        print(f"   Tables: {', '.join(stats.get('tables', []))}")
        
        # Display row counts
        if stats.get('row_counts'):
            for table, count in stats['row_counts'].items():
                print(f"   {table}: {count} rows")
    
    # Create backup
    print("\n💾 Creating initial backup...")
    try:
        success, backup_path = db.backup_database()
        if success:
            print(f"✅ Backup created: {backup_path}")
    except Exception as e:
        print(f"⚠️  Backup failed: {e}")
    
    print("\n" + "="*70)
    print("✅ DATABASE INITIALIZATION COMPLETE")
    print("="*70 + "\n")
    
    return db


if __name__ == "__main__":
    print("="*70)
    print("🗄️  DATABASE INITIALIZATION")
    print("="*70)
    
    db = init_db()
    
    # Test database write capability
    print("\n🧪 TESTING DATABASE WRITE CAPABILITY")
    print("="*70)
    
    try:
        from datetime import datetime
        import pytz
        
        wib = pytz.timezone('Asia/Jakarta')
        test_timestamp = datetime.now(wib).strftime("%Y-%m-%d %H:%M:%S")
        
        conn = db.connect()
        if conn:
            cursor = conn.cursor()
            
            # Try to insert a test record
            cursor.execute('''
                INSERT INTO flood_reports 
                ("Timestamp", "Alamat", "Tinggi Banjir", "Nama Pelapor", 
                "No HP", "IP Address", "Photo URL", "Status",
                report_date, report_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                test_timestamp,
                'TEST ADDRESS - DELETE ME',
                'Test Height',
                'Test Reporter',
                '081234567890',
                '127.0.0.1',
                'test.jpg',
                'pending',
                test_timestamp[:10],
                test_timestamp[11:19]
            ))
            
            conn.commit()
            test_id = cursor.lastrowid
            
            print(f"✅ Test write successful - ID: {test_id}")
            
            # Verify the write
            cursor.execute('SELECT * FROM flood_reports WHERE id = ?', (test_id,))
            result = cursor.fetchone()
            
            if result:
                print(f"✅ Test read successful")
                print(f"   Data: {dict(result)}")
                
                # Clean up test record
                cursor.execute('DELETE FROM flood_reports WHERE id = ?', (test_id,))
                conn.commit()
                print(f"✅ Test record cleaned up")
            else:
                print(f"❌ Could not read test record")
            
            db.close()
        else:
            print(f"❌ Could not connect to database")
    
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*70)