import os
import re
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
from flask import Flask
from telegram import Bot, Update
from telegram.ext import CommandHandler, ApplicationBuilder

# Inisialisasi Flask
app = Flask(__name__)

# Ganti dengan token bot Anda
TOKEN = '6308990102:AAFH_eAfo4imTAWnQ5CZeDUFNAC35rytnT0'

bot = Bot(token=TOKEN)

chapterCount = 0

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
    response = requests.get(text_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    return soup.select_one('pre').findChildren()

def get_chapter(url):
    """Mengambil konten bab dari URL yang diberikan."""
    global chapterCount
    chapterCount += 1
    url = requests.utils.quote(url)
    pagehtml = BeautifulSoup(requests.get(url).content, 'html.parser')
    
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
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Tambahkan halaman sampul
    pdf.add_page()
    pdf.image(cover_url, x=10, y=10, w=190)  # Sesuaikan posisi dan ukuran
    pdf.ln(100)  # Tambahkan ruang setelah gambar

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
    initial_url = requests.utils.quote(initial_url)
    html = BeautifulSoup(requests.get(initial_url).content, 'html.parser')

    author = html.select('div.author-info__username')[0].get_text()
    title = html.select('div.story-info__title')[0].get_text().strip()
    coverurl = html.select('div.story-cover img')[0]['src']

    chapterlist = list(dict.fromkeys(html.select('.story-parts ul li a')))
    chapters = []

    for item in chapterlist:
        chaptertitle, ch_text = get_chapter(f"{base_url}{item['href']}")
        chapters.append((chaptertitle, clean_text(ch_text)))

    pdf_file = create_pdf(title, author, coverurl, chapters)
    return pdf_file

def start(update: Update, context):
    """Handler untuk perintah mulai."""
    context.bot.send_message(chat_id=update.message.chat_id, text='Selamat datang! Kirimkan URL cerita Wattpad yang ingin diubah menjadi PDF.')

def convert_to_pdf(update: Update, context):
    """Mengonversi cerita Wattpad menjadi PDF."""
    if len(context.args) < 1:
        context.bot.send_message(chat_id=update.message.chat_id, text='Silakan kirim URL Wattpad yang valid.')
        return

    wattpad_url = context.args[0]
    try:
        pdf_file = get_book(wattpad_url)
        with open(pdf_file, 'rb') as file:
            context.bot.send_document(chat_id=update.message.chat_id, document=file)
    except Exception as e:
        context.bot.send_message(chat_id=update.message.chat_id, text=f'Gagal mengambil cerita dari Wattpad. Kesalahan: {e}')

def main():
    """Fungsi utama untuk menjalankan bot Telegram."""
    application = ApplicationBuilder().token(TOKEN).build()
    dispatcher = application.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("convert", convert_to_pdf))

    # Mulai polling untuk menerima pembaruan dari bot Telegram
    application.run_polling()

if __name__ == '__main__':
    # Jalankan polling di thread terpisah
    from threading import Thread
    Thread(target=main).start()
    app.run(host='0.0.0.0', port=8000)
