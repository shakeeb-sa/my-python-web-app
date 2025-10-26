import os
import csv
import requests
from flask import Flask, render_template, request, send_file
from bs4 import BeautifulSoup
import tempfile
from urllib.parse import urljoin

app = Flask(__name__)

def scrape_your_shopify_product(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return {"error": f"Failed to load page: {str(e)}"}

    soup = BeautifulSoup(response.text, 'lxml')

    # --- Extract Title from <title> tag (your HTML shows: "Product Name | Brand") ---
    title = "N/A"
    title_tag = soup.find('title')
    if title_tag:
        full_title = title_tag.get_text(strip=True)
        # Split on first "|" to remove site name (e.g., "Brown Nubuck Leather Jacket For Men | 60% Off | Famous Jackets")
        title = full_title.split('|')[0].strip()

    # --- Extract Price from Open Graph meta tags ---
    price_amount_tag = soup.find('meta', property='og:price:amount')
    price_currency_tag = soup.find('meta', property='og:price:currency')
    price = "N/A"
    if price_amount_tag and price_currency_tag:
        amount = price_amount_tag.get('content', '').strip()
        currency = price_currency_tag.get('content', '').strip()
        if amount and currency:
            price = f"{amount} {currency}"

    # --- Extract Main Image from og:image ---
    image_url = "N/A"
    og_image = soup.find('meta', property='og:image:secure_url') or soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        image_url = og_image['content'].strip()

    # --- Extract Description from meta tags ---
    description = "N/A"
    og_desc = soup.find('meta', property='og:description') or soup.find('meta', attrs={'name': 'description'})
    if og_desc and og_desc.get('content'):
        description = og_desc['content'].strip()

    return {
        "title": title,
        "price": price,
        "description": description,
        "image_url": image_url,
        "source_url": url
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form.get('url', '').strip()
    if not url:
        return render_template('result.html', error="Please enter a product URL.")

    product = scrape_your_shopify_product(url)
    if 'error' in product:
        return render_template('result.html', error=product['error'])

    # Create CSV in temporary file
    csv_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8', newline='')
    fieldnames = ['title', 'price', 'description', 'image_url', 'source_url']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerow(product)
    csv_file.close()

    return render_template(
        'result.html',
        product=product,
        csv_download=f"/download?file={csv_file.name}"
    )

@app.route('/download')
def download_file():
    file_path = request.args.get('file')
    if not file_path or not os.path.exists(file_path):
        return "File not found", 404
    return send_file(file_path, as_attachment=True, download_name="shopify_product.csv")

if __name__ == '__main__':
    app.run(debug=True)