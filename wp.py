import os
import re
import requests
from bs4 import BeautifulSoup
from flask import Flask
from telegram import Update
from telegram.ext import CommandHandler, ApplicationBuilder
import threading
from ebooklib import epub  # Pastikan untuk mengimpor pustaka ini

# Inisialisasi Flask
app = Flask(__name__)

# Ganti dengan token bot Anda
TOKEN = '6308990102:AAFH_eAfo4imTAWnQ5CZeDUFNAC35rytnT0'

chapterCount = 0

# User-Agent header
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_url(url):
    """Fetch the content of the URL with a User-Agent."""
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()  # Raises an error for bad responses
    return response.content

def get_soup(url):
    """Fetch the soup object from a URL."""
    html_content = get_url(url)
    return BeautifulSoup(html_content, 'html.parser')

def clean_text(text):
    """Membersihkan teks HTML."""
    text = re.sub(r'<p data-p-id=".{32}">', '<p>', text)
    text = re.sub(r'\xa0', '', text)
    return text

def get_page(text_url):
    """Mengambil dan menganalisis konten halaman."""
    soup = get_soup(text_url)
    content_elem = soup.select('div.panel.panel-reading p[data-p-id]')
    cleaned_content = [clean_text(str(para)) for para in content_elem]
    return ''.join(cleaned_content)

def get_chapter(url):
    """Mengambil konten bab dari URL yang diberikan."""
    global chapterCount
    chapterCount += 1
    pagehtml = get_soup(url)

    pages_re = re.compile('"pages":([0-9]*),', re.IGNORECASE)
    pages = int(pages_re.search(str(pagehtml)).group(1))

    text = []
    chaptertitle = pagehtml.select('h1.h2')[0].get_text().strip()
    text.append("<h2>{}</h2>\n".format(chaptertitle))

    for i in range(1, pages + 1):
        page_url = f"{url}/page/{i}"
        text.append('<div class="page">\n')
        page_content = get_page(page_url)
        text.append(page_content)
        text.append('</div>\n')

    chapter = "".join(text)
    return chaptertitle, chapter

def create_epub(title, author, chapters):
    """Membuat file EPUB dari informasi buku."""
    if not chapters:
        raise ValueError("Tidak ada bab yang ditemukan untuk dibuat EPUB.")

    book = epub.EpubBook()
    book.set_title(title)
    book.set_language('en')

    # Menambahkan stylesheet
    css = '''
    @page { margin: 1em; }
    body { font-family: Arial, sans-serif; line-height: 1.5; }
    h2 { color: #333; }
    '''
    
    style = epub.EpubItem(uid="style", file_name="css/main.css", media_type="text/css", content=css)
    book.add_item(style)

    # Menambahkan bab ke buku EPUB
    for chapter_title, chapter_text in chapters:
        chapter = epub.EpubHtml(title=chapter_title, file_name=f'{chapter_title}.xhtml', lang='en')
        chapter.set_content(f'''
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
            <head>
                <title>{chapter_title}</title>
                <link rel="stylesheet" href="css/main.css" type="text/css"/>
            </head>
            <body>
                <div class="chapter">
                    <h2>{chapter_title}</h2>
                    <div class="text">{chapter_text}</div>
                </div>
            </body>
        </html>''')
        book.add_item(chapter)

    # Menambahkan daftar isi
    book.toc = (epub.Link('nav.xhtml', 'Daftar Isi', 'nav'), (chapter for chapter_title, chapter_text in chapters))

    # Menambahkan item navigasi
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Menyimpan file EPUB
    epub_filename = f"{title} - {author}.epub"
    epub.write_epub(epub_filename, book)
    return epub_filename

def get_book(initial_url):
    """Mengambil detail buku dan membuat EPUB."""
    base_url = 'http://www.wattpad.com'
    
    if not initial_url.startswith("http://") and not initial_url.startswith("https://"):
        initial_url = "https://" + initial_url

    try:
        html = get_soup(initial_url)
    except Exception as e:
        raise ValueError(f"Gagal mengambil halaman: {e}")

    author_elem = html.select('div.author-info__username')
    author = author_elem[0].get_text() if author_elem else "Tidak Diketahui"

    title_elem = html.select('div.story-info__title')
    title = title_elem[0].get_text().strip() if title_elem else "Tidak Diketahui"

    chapterlist = html.select('.table-of-contents li a')
    print(f"Jumlah bab yang ditemukan: {len(chapterlist)}")  # Debugging
    chapters = []

    for item in chapterlist:
        chaptertitle, ch_text = get_chapter(f"{base_url}{item['href']}")
        chapters.append((chaptertitle, clean_text(ch_text)))

    epub_file = create_epub(title, author, chapters)
    return epub_file

async def start(update: Update, context):
    """Handler untuk perintah mulai."""
    await context.bot.send_message(chat_id=update.message.chat_id, text='Selamat datang! Kirimkan URL cerita Wattpad yang ingin diubah menjadi EPUB.')

async def convert_to_epub(update: Update, context):
    """Mengonversi cerita Wattpad menjadi EPUB."""
    if len(context.args) < 1:
        await context.bot.send_message(chat_id=update.message.chat_id, text='Silakan kirim URL Wattpad yang valid.')
        return

    wattpad_url = context.args[0]
    
    if not wattpad_url.startswith("http://") and not wattpad_url.startswith("https://"):
        wattpad_url = "https://" + wattpad_url

    try:
        epub_file = get_book(wattpad_url)
        with open(epub_file, 'rb') as file:
            await context.bot.send_document(chat_id=update.message.chat_id, document=file)
    except Exception as e:
        await context.bot.send_message(chat_id=update.message.chat_id, text=f'Gagal mengambil cerita dari Wattpad. Kesalahan: {e}')

def run_flask():
    """Menjalankan aplikasi Flask."""
    app.run(host='0.0.0.0', port=8000)

def main():
    """Fungsi utama untuk menjalankan bot Telegram."""
    application = ApplicationBuilder().token(TOKEN).build()

    # Menambahkan handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("convert_epub", convert_to_epub))

    # Mulai polling untuk menerima pembaruan dari bot Telegram
    application.run_polling()

if __name__ == '__main__':
    # Mulai Flask dalam thread terpisah
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Jalankan bot Telegram
    main()
