# Dashboard Loss Event Energi Primer

Dashboard Streamlit untuk analisis historis hambatan energi primer menggunakan:

- loss production (MWh);
- loss opportunity (Rp);
- kategori final hasil formula dan override;
- risk limit korporat dan skala dampak;
- kualitas/granularitas waktu.

## Menjalankan secara lokal

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Untuk macOS/Linux, aktivasi environment menggunakan:

```bash
source .venv/bin/activate
```

## Sumber data

Secara bawaan aplikasi membaca tab `Data_Loss_Event` dari Google Sheet proyek.
Google Sheet perlu dapat diakses melalui URL ekspor CSV. Jika belum dipublikasikan,
gunakan unggahan `.xlsx` atau `.csv` pada sidebar.

## Deployment Streamlit Community Cloud

1. Unggah `app.py`, `requirements.txt`, dan `README.md` ke repository GitHub.
2. Pilih repository tersebut di Streamlit Community Cloud.
3. Isi **Main file path** dengan `app.py`.
4. Deploy aplikasi.

## Tahap model

Versi ini adalah MVP historis. Tahap berikutnya adalah kalibrasi frekuensi dan
severity loss event, simulasi Monte Carlo, percentile P50/P80/P90/P95, serta
pemetaan probabilitas × dampak.

