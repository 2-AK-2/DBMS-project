import mysql.connector
from mysql.connector import Error
import time

config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Aasma1306'
}

def setup_database():
    conn = None
    try:
        # First connection - without database
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        print("Creating database...")
        cursor.execute("DROP DATABASE IF EXISTS memory_vault_db")
        cursor.execute("CREATE DATABASE memory_vault_db")
        cursor.close()
        conn.close()
        
        time.sleep(1)
        
        # Second connection - with database
        config_with_db = config.copy()
        config_with_db['database'] = 'memory_vault_db'
        conn = mysql.connector.connect(**config_with_db)
        cursor = conn.cursor()
        
        print("Creating tables...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                patient_id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                memory_id INT PRIMARY KEY AUTO_INCREMENT,
                patient_id INT NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                memory_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS media (
                media_id INT PRIMARY KEY AUTO_INCREMENT,
                memory_id INT NOT NULL,
                media_type VARCHAR(50),
                source_url VARCHAR(255),
                creation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (memory_id) REFERENCES memories(memory_id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_analysis (
                analysis_id INT PRIMARY KEY AUTO_INCREMENT,
                media_id INT NOT NULL,
                generated_caption TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (media_id) REFERENCES media(media_id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                tag_id INT PRIMARY KEY AUTO_INCREMENT,
                tag_name VARCHAR(100) UNIQUE NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_tags (
                memory_tag_id INT PRIMARY KEY AUTO_INCREMENT,
                memory_id INT NOT NULL,
                tag_id INT NOT NULL,
                FOREIGN KEY (memory_id) REFERENCES memories(memory_id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE,
                UNIQUE(memory_id, tag_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                audit_id INT PRIMARY KEY AUTO_INCREMENT,
                action VARCHAR(50) NOT NULL,
                table_name VARCHAR(100) NOT NULL,
                record_id INT NOT NULL,
                old_values JSON,
                new_values JSON,
                action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_info VARCHAR(255)
            )
        """)
        
        conn.commit()
        print("✓ Tables created")
        
        print("\nInserting sample data...")
        cursor.execute("DELETE FROM patients")
        cursor.execute("DELETE FROM tags")
        cursor.execute("INSERT INTO patients (patient_id, name, email) VALUES (1, 'John Doe', 'john@example.com')")
        cursor.execute("INSERT INTO tags (tag_name) VALUES ('family')")
        cursor.execute("INSERT INTO tags (tag_name) VALUES ('travel')")
        cursor.execute("INSERT INTO tags (tag_name) VALUES ('celebration')")
        cursor.execute("INSERT INTO tags (tag_name) VALUES ('personal')")
        cursor.execute("INSERT INTO tags (tag_name) VALUES ('memories')")
        conn.commit()
        print("✓ Sample data inserted")
        
        print("\nCreating functions...")
        
        cursor.execute("DROP FUNCTION IF EXISTS CountMemoriesForPatient")
        cursor.execute("""
            CREATE FUNCTION CountMemoriesForPatient(p_patient_id INT)
            RETURNS INT DETERMINISTIC READS SQL DATA
            BEGIN
                DECLARE memory_count INT DEFAULT 0;
                SELECT COUNT(*) INTO memory_count FROM memories WHERE patient_id = p_patient_id;
                RETURN COALESCE(memory_count, 0);
            END
        """)
        
        cursor.execute("DROP FUNCTION IF EXISTS GetTagCountForPatient")
        cursor.execute("""
            CREATE FUNCTION GetTagCountForPatient(p_patient_id INT)
            RETURNS INT DETERMINISTIC READS SQL DATA
            BEGIN
                DECLARE tag_count INT DEFAULT 0;
                SELECT COUNT(DISTINCT tag_id) INTO tag_count FROM memory_tags
                WHERE memory_id IN (SELECT memory_id FROM memories WHERE patient_id = p_patient_id);
                RETURN COALESCE(tag_count, 0);
            END
        """)
        
        cursor.execute("DROP FUNCTION IF EXISTS GetLatestMemoryDate")
        cursor.execute("""
            CREATE FUNCTION GetLatestMemoryDate(p_patient_id INT)
            RETURNS DATE DETERMINISTIC READS SQL DATA
            BEGIN
                DECLARE latest_date DATE;
                SELECT MAX(memory_date) INTO latest_date FROM memories WHERE patient_id = p_patient_id;
                RETURN latest_date;
            END
        """)
        
        cursor.execute("DROP FUNCTION IF EXISTS GetMediaCountForPatient")
        cursor.execute("""
            CREATE FUNCTION GetMediaCountForPatient(p_patient_id INT)
            RETURNS INT DETERMINISTIC READS SQL DATA
            BEGIN
                DECLARE media_count INT DEFAULT 0;
                SELECT COUNT(*) INTO media_count FROM media
                WHERE memory_id IN (SELECT memory_id FROM memories WHERE patient_id = p_patient_id);
                RETURN COALESCE(media_count, 0);
            END
        """)
        
        conn.commit()
        print("✓ Functions created")
        
        print("\nCreating procedures...")
        
        cursor.execute("DROP PROCEDURE IF EXISTS ProcessAndAddTags")
        cursor.execute("""
            CREATE PROCEDURE ProcessAndAddTags(IN p_memory_id INT, IN p_tags_string VARCHAR(500))
            BEGIN
                DECLARE v_tag_name VARCHAR(100);
                DECLARE v_tag_id INT;
                DECLARE v_delimiter_pos INT;
                DECLARE v_remaining_string VARCHAR(500);
                SET v_remaining_string = TRIM(p_tags_string);
                loop_tags: WHILE CHAR_LENGTH(v_remaining_string) > 0 DO
                    SET v_delimiter_pos = POSITION(',' IN v_remaining_string);
                    IF v_delimiter_pos > 0 THEN
                        SET v_tag_name = LOWER(TRIM(SUBSTRING(v_remaining_string, 1, v_delimiter_pos - 1)));
                        SET v_remaining_string = TRIM(SUBSTRING(v_remaining_string, v_delimiter_pos + 1));
                    ELSE
                        SET v_tag_name = LOWER(TRIM(v_remaining_string));
                        SET v_remaining_string = '';
                    END IF;
                    IF v_tag_name != '' THEN
                        SELECT tag_id INTO v_tag_id FROM tags WHERE tag_name = v_tag_name LIMIT 1;
                        IF v_tag_id IS NULL THEN
                            INSERT INTO tags (tag_name) VALUES (v_tag_name);
                            SET v_tag_id = LAST_INSERT_ID();
                        END IF;
                        INSERT IGNORE INTO memory_tags (memory_id, tag_id) VALUES (p_memory_id, v_tag_id);
                    END IF;
                END WHILE loop_tags;
            END
        """)
        
        cursor.execute("DROP PROCEDURE IF EXISTS AddMemoryWithTags")
        cursor.execute("""
            CREATE PROCEDURE AddMemoryWithTags(IN p_patient_id INT, IN p_title VARCHAR(255), IN p_description TEXT,
            IN p_memory_date DATE, IN p_filename VARCHAR(255), IN p_caption TEXT, IN p_tags_string VARCHAR(500),
            OUT p_new_memory_id INT, OUT p_new_media_id INT)
            BEGIN
                INSERT INTO memories (patient_id, title, description, memory_date) VALUES (p_patient_id, p_title, p_description, p_memory_date);
                SET p_new_memory_id = LAST_INSERT_ID();
                INSERT INTO media (memory_id, media_type, source_url, creation_time) VALUES (p_new_memory_id, 'photo', p_filename, NOW());
                SET p_new_media_id = LAST_INSERT_ID();
                INSERT INTO ai_analysis (media_id, generated_caption) VALUES (p_new_media_id, p_caption);
                IF p_tags_string IS NOT NULL AND p_tags_string != '' THEN
                    CALL ProcessAndAddTags(p_new_memory_id, p_tags_string);
                END IF;
            END
        """)
        
        cursor.execute("DROP PROCEDURE IF EXISTS UpdateMemoryWithTags")
        cursor.execute("""
            CREATE PROCEDURE UpdateMemoryWithTags(IN p_memory_id INT, IN p_title VARCHAR(255), IN p_description TEXT,
            IN p_memory_date DATE, IN p_tags_string VARCHAR(500))
            BEGIN
                UPDATE memories SET title = p_title, description = p_description, memory_date = p_memory_date, updated_at = CURRENT_TIMESTAMP WHERE memory_id = p_memory_id;
                DELETE FROM memory_tags WHERE memory_id = p_memory_id;
                IF p_tags_string IS NOT NULL AND p_tags_string != '' THEN
                    CALL ProcessAndAddTags(p_memory_id, p_tags_string);
                END IF;
            END
        """)
        
        cursor.execute("DROP PROCEDURE IF EXISTS DeleteMemoryWithAudit")
        cursor.execute("""
            CREATE PROCEDURE DeleteMemoryWithAudit(IN p_memory_id INT, IN p_user_info VARCHAR(255))
            BEGIN
                DECLARE v_memory_json JSON;
                SELECT JSON_OBJECT('memory_id', memory_id, 'patient_id', patient_id, 'title', title, 'description', description, 'memory_date', memory_date, 'created_at', created_at)
                INTO v_memory_json FROM memories WHERE memory_id = p_memory_id;
                INSERT INTO audit_log (action, table_name, record_id, old_values, user_info) VALUES ('DELETE', 'memories', p_memory_id, v_memory_json, p_user_info);
                DELETE FROM ai_analysis WHERE media_id IN (SELECT media_id FROM media WHERE memory_id = p_memory_id);
                DELETE FROM media WHERE memory_id = p_memory_id;
                DELETE FROM memory_tags WHERE memory_id = p_memory_id;
                DELETE FROM memories WHERE memory_id = p_memory_id;
            END
        """)
        
        cursor.execute("DROP PROCEDURE IF EXISTS GetPatientDashboardStats")
        cursor.execute("""
            CREATE PROCEDURE GetPatientDashboardStats(IN p_patient_id INT)
            BEGIN
                SELECT CountMemoriesForPatient(p_patient_id) AS total_memories,
                       GetTagCountForPatient(p_patient_id) AS total_tags,
                       GetLatestMemoryDate(p_patient_id) AS latest_memory_date,
                       GetMediaCountForPatient(p_patient_id) AS total_media;
            END
        """)
        
        conn.commit()
        print("✓ Procedures created")
        
        print("\nCreating triggers...")
        
        cursor.execute("DROP TRIGGER IF EXISTS memory_update_audit")
        cursor.execute("""
            CREATE TRIGGER memory_update_audit AFTER UPDATE ON memories FOR EACH ROW
            BEGIN
                INSERT INTO audit_log (action, table_name, record_id, old_values, new_values)
                VALUES ('UPDATE', 'memories', NEW.memory_id,
                JSON_OBJECT('title', OLD.title, 'description', OLD.description, 'memory_date', OLD.memory_date),
                JSON_OBJECT('title', NEW.title, 'description', NEW.description, 'memory_date', NEW.memory_date));
            END
        """)
        
        cursor.execute("DROP TRIGGER IF EXISTS memory_delete_audit")
        cursor.execute("""
            CREATE TRIGGER memory_delete_audit BEFORE DELETE ON memories FOR EACH ROW
            BEGIN
                INSERT INTO audit_log (action, table_name, record_id, old_values)
                VALUES ('DELETE', 'memories', OLD.memory_id,
                JSON_OBJECT('memory_id', OLD.memory_id, 'patient_id', OLD.patient_id, 'title', OLD.title, 'description', OLD.description, 'memory_date', OLD.memory_date));
            END
        """)
        
        cursor.execute("DROP TRIGGER IF EXISTS media_insert_audit")
        cursor.execute("""
            CREATE TRIGGER media_insert_audit AFTER INSERT ON media FOR EACH ROW
            BEGIN
                INSERT INTO audit_log (action, table_name, record_id, new_values)
                VALUES ('INSERT', 'media', NEW.media_id,
                JSON_OBJECT('media_id', NEW.media_id, 'memory_id', NEW.memory_id, 'media_type', NEW.media_type, 'source_url', NEW.source_url));
            END
        """)
        
        conn.commit()
        print("✓ Triggers created")
        
        print("\n" + "=" * 60)
        print("✅ DATABASE SETUP COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\n📊 Created:")
        print("   • 7 Tables")
        print("   • 4 Functions")
        print("   • 4 Stored Procedures")
        print("   • 3 Triggers")
        print("\n🚀 You can now run: python3 app.py")
        print("=" * 60 + "\n")
        
    except Error as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    setup_database()