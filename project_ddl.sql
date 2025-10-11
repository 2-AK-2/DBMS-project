CREATE DATABASE IF NOT EXISTS memory_vault_db;
USE memory_vault_db;

-- TABLES (DDL Commands)
CREATE TABLE IF NOT EXISTS users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('patient', 'family', 'caregiver', 'admin') NOT NULL
);

CREATE TABLE IF NOT EXISTS patients (
    patient_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT UNIQUE NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS memories (
    memory_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    memory_date DATE,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS media (
    media_id INT PRIMARY KEY AUTO_INCREMENT,
    memory_id INT NOT NULL,
    media_type ENUM('photo', 'video', 'audio') NOT NULL,
    source_url VARCHAR(2048) NOT NULL,
    creation_time DATETIME,
    FOREIGN KEY (memory_id) REFERENCES memories(memory_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ai_analysis (
    analysis_id INT PRIMARY KEY AUTO_INCREMENT,
    media_id INT UNIQUE NOT NULL,
    generated_caption TEXT,
    FOREIGN KEY (media_id) REFERENCES media(media_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tags (
    tag_id INT PRIMARY KEY AUTO_INCREMENT,
    tag_name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_tags (
    memory_id INT,
    tag_id INT,
    PRIMARY KEY (memory_id, tag_id),
    FOREIGN KEY (memory_id) REFERENCES memories(memory_id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE
);

-- New table for the trigger
CREATE TABLE IF NOT EXISTS memory_log (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    memory_id_deleted INT,
    deleted_title VARCHAR(255),
    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Stored Procedure: To add a new memory and its media/caption in one go.
DELIMITER $$
CREATE PROCEDURE AddFullMemory(
    IN p_patient_id INT,
    IN p_title VARCHAR(255),
    IN p_description TEXT,
    IN p_memory_date DATE,
    IN p_filename VARCHAR(2048),
    IN p_caption TEXT
)
BEGIN
    DECLARE new_memory_id INT;
    DECLARE new_media_id INT;

    -- Insert into memories table
    INSERT INTO memories (patient_id, title, description, memory_date) 
    VALUES (p_patient_id, p_title, p_description, p_memory_date);
    SET new_memory_id = LAST_INSERT_ID();

    -- Insert into media table
    INSERT INTO media (memory_id, media_type, source_url, creation_time) 
    VALUES (new_memory_id, 'photo', p_filename, NOW());
    SET new_media_id = LAST_INSERT_ID();

    -- Insert into ai_analysis table
    INSERT INTO ai_analysis (media_id, generated_caption) 
    VALUES (new_media_id, p_caption);

    -- Return the ID of the new memory
    SELECT new_memory_id;
END$$
DELIMITER ;

-- Function: To count the total number of memories for a patient.
DELIMITER $$
CREATE FUNCTION CountPatientMemories(p_patient_id INT)
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE memory_count INT;
    SELECT COUNT(*) INTO memory_count FROM memories WHERE patient_id = p_patient_id;
    RETURN memory_count;
END$$
DELIMITER ;

-- Trigger: To log a memory's details before it is deleted.
DELIMITER $$
CREATE TRIGGER before_memory_delete
BEFORE DELETE ON memories
FOR EACH ROW
BEGIN
    INSERT INTO memory_log (memory_id_deleted, deleted_title)
    VALUES (OLD.memory_id, OLD.title);
END$$
DELIMITER ;
