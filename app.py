import streamlit as st
import sqlite3
import pandas as pd
import json
import csv
import io
from datetime import datetime

# Функция для проверки пароля (пароль теперь в секретах Streamlit)
def check_password(password):
    correct_password = st.secrets.get("EDIT_PASSWORD", "default_password")
    return password == correct_password

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('words.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS texts
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         name TEXT NOT NULL UNIQUE)
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS words
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         text_id INTEGER,
         lemma TEXT NOT NULL,
         forms TEXT,
         translation TEXT,
         comments TEXT)
    ''')
    
    # Автоматически создаем тексты если их нет
    default_texts = ["Текст1", "Текст2", "Текст3", "Текст4", "Текст5"]
    for text_name in default_texts:
        c.execute("INSERT OR IGNORE INTO texts (name) VALUES (?)", (text_name,))
    
    conn.commit()
    conn.close()

def delete_word(word_id):
    conn = sqlite3.connect('words.db')
    c = conn.cursor()
    c.execute("DELETE FROM words WHERE id = ?", (word_id,))
    conn.commit()
    conn.close()

def update_word(word_id, lemma, forms, translation, comments):
    """Обновляет слово в базе данных"""
    conn = sqlite3.connect('words.db')
    c = conn.cursor()
    try:
        c.execute("UPDATE words SET lemma = ?, forms = ?, translation = ?, comments = ? WHERE id = ?",
                 (lemma, forms, translation, comments, word_id))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

def add_text(text_name):
    conn = sqlite3.connect('words.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO texts (name) VALUES (?)", (text_name,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def rename_text(text_id, new_name):
    conn = sqlite3.connect('words.db')
    c = conn.cursor()
    try:
        c.execute("UPDATE texts SET name = ? WHERE id = ?", (new_name, text_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_texts():
    conn = sqlite3.connect('words.db')
    texts = pd.read_sql("SELECT * FROM texts ORDER BY name", conn)
    conn.close()
    return texts

# ФУНКЦИИ ЭКСПОРТА/ИМПОРТА
def export_data():
    """Экспортирует все данные в JSON"""
    conn = sqlite3.connect('words.db')
    
    # Получаем тексты
    texts_df = pd.read_sql("SELECT * FROM texts", conn)
    
    # Получаем слова
    words_df = pd.read_sql("SELECT * FROM words ORDER BY id", conn)  # Старые сверху
    
    conn.close()
    
    data = {
        'export_date': datetime.now().isoformat(),
        'texts': texts_df.to_dict('records'),
        'words': words_df.to_dict('records')
    }
    
    return json.dumps(data, ensure_ascii=False, indent=2)

def export_csv():
    """Экспортирует слова в CSV"""
    conn = sqlite3.connect('words.db')
    
    # Объединяем слова с названиями текстов
    words_df = pd.read_sql('''
        SELECT w.*, t.name as text_name 
        FROM words w 
        LEFT JOIN texts t ON w.text_id = t.id
        ORDER BY w.id  -- Старые сверху
    ''', conn)
    
    conn.close()
    
    # Создаем CSV в памяти
    output = io.StringIO()
    words_df.to_csv(output, index=False, encoding='utf-8')
    return output.getvalue()

def import_data(json_data):
    """Импортирует данные из JSON"""
    try:
        data = json.loads(json_data)
        
        conn = sqlite3.connect('words.db')
        c = conn.cursor()
        
        # Очищаем текущие данные
        c.execute("DELETE FROM words")
        c.execute("DELETE FROM texts")
        
        # Импортируем тексты
        for text in data['texts']:
            c.execute("INSERT INTO texts (id, name) VALUES (?, ?)", 
                     (text['id'], text['name']))
        
        # Импортируем слова
        for word in data['words']:
            c.execute("INSERT INTO words (id, text_id, lemma, forms, translation, comments) VALUES (?, ?, ?, ?, ?, ?)",
                     (word['id'], word['text_id'], word['lemma'], word['forms'], word['translation'], word['comments']))
        
        conn.commit()
        conn.close()
        return True, "Данные успешно импортированы!"
    
    except Exception as e:
        return False, f"Ошибка импорта: {str(e)}"

def get_stats():
    """Статистика словаря"""
    conn = sqlite3.connect('words.db')
    
    # Общее количество слов
    total_words = pd.read_sql("SELECT COUNT(*) as count FROM words", conn).iloc[0]['count']
    
    # Количество слов по текстам
    words_by_text = pd.read_sql('''
        SELECT t.name, COUNT(w.id) as word_count 
        FROM texts t 
        LEFT JOIN words w ON t.id = w.text_id 
        GROUP BY t.id, t.name 
        ORDER BY t.name
    ''', conn)
    
    conn.close()
    
    return total_words, words_by_text

# Инициализируем базу
init_db()

st.set_page_config(page_title="Греческий словарь", layout="wide")

# ПРОВЕРКА ПАРОЛЯ В НАЧАЛЕ
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Если не авторизован - показываем форму входа
if not st.session_state.authenticated:
    st.title("греки греки греки")
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.info("Введите пароль для редактирования или нажмите 'Только просмотр'")
        
        password = st.text_input("Пароль:", type="password")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Войти в режим редактирования"):
                if check_password(password):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Неверный пароль")
        
        with col_btn2:
            if st.button("Только просмотр"):
                st.session_state.authenticated = True
                st.session_state.view_only = True
                st.rerun()
    
    st.stop()

# ОСНОВНОЕ ПРИЛОЖЕНИЕ
st.title("греки греки греки")

# Боковая панель
with st.sidebar:
    # Статистика
    total_words, words_by_text = get_stats()
    st.header("Статистика")
    st.metric("Всего слов", total_words)
    
    if not words_by_text.empty:
        with st.expander("Слова по текстам"):
            for _, row in words_by_text.iterrows():
                st.write(f"{row['name']}: {row['word_count']} слов")
    
    st.write("---")
    
    # Информация о сортировке
    st.header("Порядок слов")
    st.info("Старые слова → сверху\nНовые слова → снизу")
    
    st.write("---")
    
    # Статус режима
    if st.session_state.get('view_only'):
        st.error("РЕЖИМ ПРОСМОТРА")
        st.info("Вы можете только просматривать слова. Для редактирования введите пароль.")
        
        if st.button("Войти с паролем"):
            st.session_state.authenticated = False
            st.rerun()
    else:
        st.success("РЕЖИМ РЕДАКТИРОВАНИЯ")
        st.info("Вы можете добавлять, редактировать и удалять слова.")
        
        if st.button("Выйти из аккаунта"):
            st.session_state.authenticated = False
            st.session_state.view_only = False
            st.rerun()
    
    st.write("---")
    
    # Резервное копирование (только в режиме редактирования)
    if not st.session_state.get('view_only'):
        st.header("Резервное копирование")
        
        with st.expander("Экспорт данных"):
            st.info("Скачайте резервную копию вашего словаря")
            
            # Экспорт JSON
            json_data = export_data()
            st.download_button(
                label="📥 Скачать JSON",
                data=json_data,
                file_name=f"greek_dictionary_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )
            
            # Экспорт CSV
            csv_data = export_csv()
            st.download_button(
                label="Скачать CSV",
                data=csv_data,
                file_name=f"greek_dictionary_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        
        with st.expander("Импорт данных"):
            st.warning("Внимание: импорт перезапишет все текущие данные!")
            
            uploaded_file = st.file_uploader("Выберите JSON файл", type=['json'])
            
            if uploaded_file is not None:
                json_data = uploaded_file.getvalue().decode('utf-8')
                
                if st.button("Импортировать данные", type="primary"):
                    success, message = import_data(json_data)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    
    # Управление текстами (только в режиме редактирования)
    if not st.session_state.get('view_only'):
        st.header("📁 Управление текстами")
        
        # Добавление нового текста
        with st.expander("Добавить текст"):
            with st.form("add_text_form"):
                new_text_name = st.text_input("Название текста", placeholder="Текст6")
                if st.form_submit_button("Добавить текст") and new_text_name:
                    if add_text(new_text_name):
                        st.success(f"Текст '{new_text_name}' добавлен!")
                        st.rerun()
                    else:
                        st.error("Текст с таким названием уже существует!")
        
        # Переименование текстов
        with st.expander("Переименовать текст"):
            texts_df = get_texts()
            for _, text in texts_df.iterrows():
                with st.form(f"rename_{text['id']}"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        new_name = st.text_input(
                            "Новое название", 
                            value=text['name'],
                            key=f"rename_input_{text['id']}"
                        )
                    with col2:
                        if st.form_submit_button("💾", help="Сохранить"):
                            if new_name and new_name != text['name']:
                                if rename_text(text['id'], new_name):
                                    st.success(f"✅ Переименован в '{new_name}'!")
                                    st.rerun()
                                else:
                                    st.error("❌ Такое название уже существует!")

# Получаем текущие тексты из базы
texts_df = get_texts()

# Создаем вкладки
if not texts_df.empty:
    tab_names = [f"{row['name']}" for _, row in texts_df.iterrows()]
    tabs = st.tabs(tab_names)

    # Для каждой вкладки
    for i, (_, text) in enumerate(texts_df.iterrows()):
        with tabs[i]:
            st.subheader(f"{text['name']}")
            
            # Добавление слова (только в режиме редактирования)
            if not st.session_state.get('view_only'):
                with st.expander("Добавить слово"):
                    with st.form(f"add_word_{text['id']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            lemma = st.text_input("Лексема*", placeholder="λύω", key=f"lemma_{text['id']}")
                            forms = st.text_area("Основные формы", placeholder="λύω, λύσω, ἔλυσα, λέλυκα...", key=f"forms_{text['id']}")
                        
                        with col2:
                            translation = st.text_input("Перевод", placeholder="освобождать, развязывать", key=f"trans_{text['id']}")
                            comments = st.text_area("Комментарии", placeholder="Мои заметки...", key=f"comments_{text['id']}")
                        
                        if st.form_submit_button("Добавить слово") and lemma:
                            conn = sqlite3.connect('words.db')
                            c = conn.cursor()
                            c.execute("INSERT INTO words (text_id, lemma, forms, translation, comments) VALUES (?, ?, ?, ?, ?)",
                                     (text['id'], lemma, forms, translation, comments))
                            conn.commit()
                            conn.close()
                            st.success(f"Слово '{lemma}' добавлено в '{text['name']}'!")
                            st.rerun()
            else:
                st.info("🔒 Для добавления слов требуется пароль")
            
            # Поиск и отображение слов этого текста
            st.write("---")
            search = st.text_input(f"Поиск в '{text['name']}'", key=f"search_{text['id']}")
            
            conn = sqlite3.connect('words.db')
            
            # ФИКСИРОВАННАЯ СОРТИРОВКА: старые сверху, новые снизу
            if search:
                words = pd.read_sql(
                    "SELECT * FROM words WHERE text_id = ? AND (lemma LIKE ? OR translation LIKE ?) ORDER BY id",
                    conn, params=(text['id'], f'%{search}%', f'%{search}%')
                )
            else:
                words = pd.read_sql(
                    "SELECT * FROM words WHERE text_id = ? ORDER BY id",
                    conn, params=(text['id'],)
                )
            conn.close()
            
            if not words.empty:
                st.write(f"Слов в словаре:*{len(words)}")
                for _, word in words.iterrows():
                    with st.expander(f"{word['lemma']} - {word['translation']}"):
                        # Режим просмотра
                        if st.session_state.get('view_only'):
                            st.write(f"Формы: {word['forms'] or '-'}")
                            if word['comments']:
                                st.write(f"Комментарии: {word['comments']}")
                        
                        # Режим редактирования
                        else:
                            with st.form(f"edit_word_{word['id']}"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    new_lemma = st.text_input("Лексема", value=word['lemma'], key=f"edit_lemma_{word['id']}")
                                    new_forms = st.text_area("Основные формы", value=word['forms'] or "", key=f"edit_forms_{word['id']}")
                                
                                with col2:
                                    new_translation = st.text_input("Перевод", value=word['translation'] or "", key=f"edit_trans_{word['id']}")
                                    new_comments = st.text_area("Комментарии", value=word['comments'] or "", key=f"edit_comments_{word['id']}")
                                
                                col_btn1, col_btn2 = st.columns(2)
                                with col_btn1:
                                    if st.form_submit_button("💾 Сохранить"):
                                        if update_word(word['id'], new_lemma, new_forms, new_translation, new_comments):
                                            st.success("Слово обновлено!")
                                            st.rerun()
                                
                                with col_btn2:
                                    if st.form_submit_button("Удалить"):
                                        delete_word(word['id'])
                                        st.rerun()
            else:
                st.info("В этом тексте пока нет слов.")
else:
    st.info("Пока нет текстов.")

# Сообщение о режиме внизу
st.write("---")
if st.session_state.get('view_only'):
    st.info("Режим просмотра - для редактирования нажмите 'Войти с паролем' в боковой панели")
else:
    st.success("Режим редактирования - вы можете добавлять, редактировать и удалять слова")
