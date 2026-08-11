import sqlite3

def run():
    conn = sqlite3.connect('stylesync.db')
    cursor = conn.cursor()
    
    # Find duplicate names and keep only the minimum rowid
    # Since ID is a UUID, we can just use the SQLite internal rowid to figure out which one to keep
    cursor.execute("""
        DELETE FROM wardrobe_items 
        WHERE rowid NOT IN (
            SELECT MIN(rowid) 
            FROM wardrobe_items 
            GROUP BY name
        )
    """)
    
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    print(f"Deleted {deleted_count} duplicate items.")

if __name__ == "__main__":
    run()
