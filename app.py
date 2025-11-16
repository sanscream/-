import streamlit as st
import sqlite3
import pandas as pd
import hashlib

# ПАРОЛЬ для редактирования
EDIT_PASSWORD = "greek1234"

# Функция для проверки пароля
def check_password(password):
    return password == EDIT_PASSWORD

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
         comments TEXT,
         FOREIGN KEY (text_id) REFERENCES texts (id))
    ''')
    
    # Автоматически создаем тексты если их нет
    default_texts = ["Текст1", "Текст2", "Текст3", "Текст4", "Текст5"]
    for text_name in default_texts:
        c.execute("INSERT OR IGNORE INTO texts (name) VALUES (?)", (text_name,))
    
    conn.commit()
    conn.close()

def migrate_db():
    """Обновляет структуру базы данных если она старая"""
    conn = sqlite3.connect('words.db')
    c = conn.cursor()
    
    # Проверяем существующие таблицы
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='words'")
    if c.fetchone():
        # Проверяем есть ли колонка text_id
        c.execute("PRAGMA table_info(words)")
        columns = [col[1] for col in c.fetchall()]
        
        if 'text_id' not in columns:
            # Старая структура - нужно мигрировать
            st.warning("Обновляем структуру базы данных...")
            
            # Создаем новую таблицу с правильной структурой
            c.execute('''
                CREATE TABLE words_new 
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 text_id INTEGER,
                 lemma TEXT NOT NULL,
                 forms TEXT,
                 translation TEXT,
                 comments TEXT)
            ''')
            
            # Переносим все старые данные в text_id = 1 (Текст1)
            c.execute("INSERT INTO words_new (text_id, lemma, forms, translation, comments) SELECT 1, lemma, forms, translation, comments FROM words")
            
            # Удаляем старую таблицу и переименовываем новую
            c.execute("DROP TABLE words")
            c.execute("ALTER TABLE words_new RENAME TO words")
            
            st.success("База данных обновлена!")
    
    conn.commit()
    conn.close()

def delete_word(word_id):
    conn = sqlite3.connect('words.db')
    c = conn.cursor()
    c.execute("DELETE FROM words WHERE id = ?", (word_id,))
    conn.commit()
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

# Инициализируем и мигрируем базу
init_db()
migrate_db()

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
                    st.error("❌ Неверный пароль")
        
        with col_btn2:
            if st.button("Только просмотр"):
                st.session_state.authenticated = True
                st.session_state.view_only = True
                st.rerun()
    
    st.stop()  # Останавливаем выполнение дальше

# ОСНОВНОЕ ПРИЛОЖЕНИЕ (после авторизации)
st.title("греки греки греки")

# Боковая панель
with st.sidebar:
    # Статус режима
    if st.session_state.get('view_only'):
        st.error("РЕЖИМ ПРОСМОТРА")
        st.info("Вы можете только просматривать слова. Для редактирования введите пароль.")
        
        if st.button("Войти с паролем"):
            st.session_state.authenticated = False
            st.rerun()
    else:
        st.success("РЕЖИМ РЕДАКТИРОВАНИЯ")
        st.info("Вы можете добавлять и удалять слова.")
        
        if st.button("Выйти из аккаунта"):
            st.session_state.authenticated = False
            st.session_state.view_only = False
            st.rerun()
    
    st.write("---")
    
    # Управление текстами (только в режиме редактирования)
    if not st.session_state.get('view_only'):
        st.header("📁 Управление текстами")
        
        # Добавление нового текста
        with st.expander("Добавить текст"):
            with st.form("add_text_form"):
                new_text_name = st.text_input("Название текста", placeholder="Текст6")
                if st.form_submit_button("Добавить текст") and new_text_name:
                    if add_text(new_text_name):
                        st.success(f"✅ Текст '{new_text_name}' добавлен!")
                        st.rerun()
                    else:
                        st.error("❌ Текст с таким названием уже существует!")
        
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
            if search:
                words = pd.read_sql(
                    "SELECT * FROM words WHERE text_id = ? AND (lemma LIKE ? OR translation LIKE ?) ORDER BY lemma",
                    conn, params=(text['id'], f'%{search}%', f'%{search}%')
                )
            else:
                words = pd.read_sql(
                    "SELECT * FROM words WHERE text_id = ? ORDER BY lemma",
                    conn, params=(text['id'],)
                )
            conn.close()
            
            if not words.empty:
                st.write(f"**Слов в словаре:** {len(words)}")
                for _, word in words.iterrows():
                    with st.expander(f"**{word['lemma']}** - {word['translation']}"):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**Формы:** {word['forms'] or '—'}")
                            if word['comments']:
                                st.write(f"**Комментарии:** {word['comments']}")
                        with col2:
                            # Кнопка удаления только в режиме редактирования
                            if not st.session_state.get('view_only'):
                                if st.button("Удалить", key=f"delete_{word['id']}"):
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
    st.success("Режим редактирования - вы можете изменять словарь")
