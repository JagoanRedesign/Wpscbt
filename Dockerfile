# Menggunakan image Python sebagai base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Menyalin file requirements.txt dan skrip Python ke dalam container
COPY requirements.txt .
COPY wp.py .

# Menginstal dependensi
RUN pip install --no-cache-dir -r requirements.txt

# Mengupgrade fpdf atau fpdf ke versi terbaru
RUN pip install --no-cache-dir --upgrade fpdf2  # Ganti dengan fpdf jika perlu

# Menjalankan aplikasi Flask
CMD ["python", "wp.py"]
