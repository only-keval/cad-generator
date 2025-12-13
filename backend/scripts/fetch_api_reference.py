from bs4 import BeautifulSoup
import requests

if __name__ == '__main__':
    url = "https://cadquery.readthedocs.io/en/latest/apireference.html"
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    # get element with id="api-reference"
    api_reference_elem = soup.find(id="api-reference")
    if api_reference_elem is not None:
        soup = api_reference_elem
    text = soup.get_text(separator="")

    save_path = "data/cadquery_api_reference.txt"
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"API reference fetched and saved to {save_path}")
