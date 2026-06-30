import os
import urllib.request
import zipfile
import sys

def download_and_extract():
    url = "https://nodejs.org/dist/v20.18.0/node-v20.18.0-win-x64.zip"
    workspace = r"C:\Users\Dell\DAY 2 AGENTIC AI"
    zip_path = os.path.join(workspace, "node.zip")
    extract_path = os.path.join(workspace, "node")

    if not os.path.exists(extract_path):
        os.makedirs(extract_path)

    print(f"Downloading Node.js from {url}...")
    try:
        urllib.request.urlretrieve(url, zip_path)
        print("Download complete. Extracting...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        print("Extraction complete.")
        
        # Clean up zip file
        os.remove(zip_path)
        print("Cleaned up ZIP file.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    download_and_extract()
