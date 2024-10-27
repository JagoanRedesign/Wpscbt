import os
import re
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
from flask import Flask
from telegram import Update
from telegram.ext import CommandHandler, ApplicationBuilder
import threading


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

def get_cover(cover_url, cover_file):
    """Mengambil dan menyimpan gambar sampul."""
    try:
        response = requests.get(cover_url)
        with open(cover_file, 'wb') as f:
            f.write(response.content)
        return 1
    except Exception as error:
        print("Tidak dapat mengambil sampul:", error)
        return 0

def clean_text(text):
    """Membersihkan teks HTML."""
    text = re.sub(r'<p data-p-id=".{32}">', '<p>', text)
    text = re.sub(r'\xa0', '', text)
    return text

def get_page(text_url):
    """Mengambil dan menganalisis konten halaman."""
    text_url = requests.utils.quote(text_url)
    text = get_soup(text_url).select_one('pre').findChildren()
    return text

def get_chapter(url):
    """Mengambil konten bab dari URL yang diberikan."""
    global chapterCount
    url = requests.utils.quote(url)
    chapterCount += 1
    pagehtml = get_soup(url)

    pages_re = re.compile('"pages":([0-9]*),', re.IGNORECASE)
    pages = int(pages_re.search(str(pagehtml)).group(1))

    text = []
    chaptertitle = pagehtml.select('h1.h2')[0].get_text().strip()
    text.append("<h2>{}</h2>\n".format(chaptertitle))

    for i in range(1, pages + 1):
        page_url = url + "/page/" + str(i)
        text.append('<div class="page">\n')
        for j in get_page(page_url):
            text.append(j.prettify())
        text.append('</div>\n')

    chapter = "".join(text)
    return chaptertitle, chapter

def create_pdf(title, author, cover_url, chapters):
    """Membuat file PDF dari informasi buku."""
    if not chapters:
        raise ValueError("Tidak ada bab yang ditemukan untuk dibuat PDF.")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Tambahkan halaman sampul
    pdf.add_page()

    # Cek format gambar
    if cover_url.lower().endswith(('.jpg', '.jpeg', '.png')):
        try:
            pdf.image(cover_url, x=10, y=10, w=190)
        except Exception as e:
            print(f"Kesalahan saat menambahkan gambar: {e}")
            pdf.cell(200, 10, txt="Gambar sampul tidak dapat dimuat.", ln=True, align='C')
    else:
        pdf.cell(200, 10, txt="Format gambar tidak didukung.", ln=True, align='C')

    pdf.ln(100)  # Tambahkan ruang setelah gambar

    # Set font default
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Judul: {title}", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Penulis: {author}", ln=True, align='C')
    pdf.cell(200, 10, ln=True)  # Tambahkan baris kosong

    for chapter_title, chapter_text in chapters:
        pdf.add_page()
        pdf.set_font("Arial", 'B', size=14)
        pdf.cell(200, 10, txt=chapter_title, ln=True)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, chapter_text)

    pdf_file = f"{title} - {author}.pdf"
    pdf.output(pdf_file)
    return pdf_file

def get_book(initial_url):
    """Mengambil detail buku dan membuat PDF."""
    base_url = 'http://www.wattpad.com'
    
    # Pastikan URL memiliki skema yang benar
    if not initial_url.startswith("http://") and not initial_url.startswith("https://"):
        initial_url = "https://" + initial_url

    # Mengambil konten halaman
    try:
        html = get_soup(initial_url)
    except Exception as e:
        raise ValueError(f"Gagal mengambil halaman: {e}")

    # Ambil informasi penulis
    author_elem = html.select('div.author-info__username')
    author = author_elem[0].get_text() if author_elem else "Tidak Diketahui"

    # Ambil informasi judul
    title_elem = html.select('div.story-info__title')
    title = title_elem[0].get_text().strip() if title_elem else "Tidak Diketahui"

    # Ambil URL sampul
    cover_elem = html.select('div.story-cover img')
    coverurl = cover_elem[0]['src'] if cover_elem else ""

    # Ambil daftar bab
    chapterlist = html.select('.table-of-contents li a')
    print(f"Jumlah bab yang ditemukan: {len(chapterlist)}")  # Debugging
    chapters = []

    # Mengambil setiap bab
    for item in chapterlist:
        chaptertitle, ch_text = get_chapter(f"{base_url}{item['href']}")
        chapters.append((chaptertitle, clean_text(ch_text)))

    # Membuat PDF
    pdf_file = create_pdf(title, author, coverurl, chapters)
    return pdf_file

async def start(update: Update, context):
    """Handler untuk perintah mulai."""
    await context.bot.send_message(chat_id=update.message.chat_id, text='Selamat datang! Kirimkan URL cerita Wattpad yang ingin diubah menjadi PDF.')

async def convert_to_pdf(update: Update, context):
    """Mengonversi cerita Wattpad menjadi PDF."""
    if len(context.args) < 1:
        await context.bot.send_message(chat_id=update.message.chat_id, text='Silakan kirim URL Wattpad yang valid.')
        return

    wattpad_url = context.args[0]
    
    if not wattpad_url.startswith("http://") and not wattpad_url.startswith("https://"):
        wattpad_url = "https://" + wattpad_url

    try:
        pdf_file = get_book(wattpad_url)
        with open(pdf_file, 'rb') as file:
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
    application.add_handler(CommandHandler("convert_pdf", convert_to_pdf))

    # Mulai polling untuk menerima pembaruan dari bot Telegram
    application.run_polling()

if __name__ == '__main__':
    # Mulai Flask dalam thread terpisah
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Jalankan bot Telegram
    main()
