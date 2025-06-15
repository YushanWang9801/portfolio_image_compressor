import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv


def main():
    load_dotenv()
    collection_name = os.getenv("COLLECTION_NAME")
    output_dir = os.getenv("OUTPUT_DIR")
    config_filepath = os.getenv("FIREBASE_CONFIG")

    if not collection_name:
        raise ValueError("COLLECTION_NAME not found in .env file")

    try:
        cred = credentials.Certificate(config_filepath)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
    except Exception as e:
        print(f"Firebase Credential Error: {e}")
        return

    os.makedirs(output_dir, exist_ok=True)
    collection_ref = db.collection(collection_name)
    print(f"Downloading collection: {collection_name}")

    docs = collection_ref.stream()

    success_count = 0
    for doc in docs:
        doc_data = doc.to_dict()
        doc_id = doc.id
        file_name = f"{doc_id}.json"
        file_path = os.path.join(output_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(
                {"id": doc_id, "data": convert_firestore_types(doc_data)},
                f,
                ensure_ascii=False,
                indent=2,
            )

        success_count += 1
        print(f"✅ Document saved: {file_name}")

    print(f"\nDownload completed! Total documents: {success_count}")
    print(f"Documents saved to: {os.path.abspath(output_dir)}")


def convert_firestore_types(data):
    if isinstance(data, dict):
        return {k: convert_firestore_types(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_firestore_types(item) for item in data]
    elif hasattr(data, "_path"):  # DocumentReference
        return {"__reference__": data.path}
    elif hasattr(data, "__class__") and data.__class__.__name__ == "Timestamp":
        return {"__timestamp__": data.isoformat()}
    elif hasattr(data, "to_eng_string"):  # GeoPoint
        return {"__geopoint__": f"{data.latitude},{data.longitude}"}
    return data


if __name__ == "__main__":
    main()
