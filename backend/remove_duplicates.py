import sqlite3

def run():
    conn = sqlite3.connect('stylesync.db')
    cursor = conn.cursor()
    
    # Find duplicate items per user (matching user_id and normalized name) and keep only MIN(rowid)
    cursor.execute("""
        DELETE FROM wardrobe_items 
        WHERE rowid NOT IN (
            SELECT MIN(rowid) 
            FROM wardrobe_items 
            GROUP BY user_id, LOWER(TRIM(name))
        )
    """)
    deleted_count = cursor.rowcount

    # Clean up any orphaned item embeddings whose wardrobe item was deleted
    cursor.execute("""
        DELETE FROM item_embeddings
        WHERE item_id NOT IN (
            SELECT id FROM wardrobe_items
        )
    """)
    deleted_embeddings = cursor.rowcount
    
    conn.commit()
    conn.close()
    print(f"Deleted {deleted_count} duplicate items and {deleted_embeddings} orphaned embeddings.")

if __name__ == "__main__":
    run()

