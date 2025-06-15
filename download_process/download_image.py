import os
import requests
import json
from concurrent.futures import ThreadPoolExecutor


def download_image(item):
    tag_dir = os.path.join("output", item["tag"])
    os.makedirs(tag_dir, exist_ok=True)

    save_path = os.path.join(tag_dir, item["name"])
    if os.path.exists(save_path):
        print(f"文件已存在，跳过: {save_path}")
        return

    try:
        response = requests.get(item["url"], stream=True)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"成功下载: {save_path}")
    except Exception as e:
        print(f"下载失败 {item['url']}: {str(e)}")


def main():
    with open("./output/image_data.json", "r") as f:
        data = json.load(f)

    os.makedirs("output", exist_ok=True)

    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(download_image, data)


if __name__ == "__main__":
    main()
