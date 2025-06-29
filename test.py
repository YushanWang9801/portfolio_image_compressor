import os
import json
import time
import firebase_admin
from firebase_admin import credentials, firestore
from google.api_core import exceptions, retry
from dotenv import load_dotenv


def main():
    # 加载配置
    load_dotenv()
    collection_name = os.getenv("COLLECTION_NAME")
    output_dir = os.getenv("OUTPUT_DIR", "downloaded_data")
    config_filepath = os.getenv("FIREBASE_CONFIG")

    # 初始化 Firebase
    try:
        cred = credentials.Certificate(config_filepath)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
    except Exception as e:
        print(f"🔥 Firebase 初始化失败: {type(e).__name__}: {str(e)}")
        return

    # 测试连接
    test_connection(db, collection_name)

    # 分批下载
    download_collection(db, collection_name, output_dir)


def test_connection(db, collection_name):
    """测试 Firestore 连接性"""
    print("\n=== 连接测试 ===")
    start_time = time.time()

    try:
        # 测试元数据访问
        db.collection(collection_name).document("__test_doc__").set(
            {"test": time.time()}
        )
        latency = (time.time() - start_time) * 1000
        print(f"✅ 连接成功! 延迟: {latency:.2f}ms")
        return True
    except exceptions.PermissionDenied:
        print("❌ 权限不足 - 请检查服务账号是否有 Firestore 读写权限")
    except exceptions.DeadlineExceeded:
        print("❌ 连接超时 - 可能是网络问题或防火墙阻止")
    except Exception as e:
        print(f"❌ 连接失败: {type(e).__name__}: {str(e)}")
    return False


def download_collection(db, collection_name, output_dir):
    """分批下载集合数据"""
    print(f"\n📂 开始下载集合: {collection_name}")
    os.makedirs(output_dir, exist_ok=True)

    # 自定义重试策略
    custom_retry = retry.Retry(
        initial=1.0,
        maximum=60.0,
        multiplier=2.0,
        predicate=retry.if_exception_type(
            exceptions.DeadlineExceeded, exceptions.ResourceExhausted
        ),
    )

    last_doc = None
    batch_size = 50
    total_count = 0
    start_time = time.time()

    while True:
        try:
            # 构建分页查询
            query = db.collection(collection_name)
            query = query.order_by("__name__").limit(batch_size)
            if last_doc:
                query = query.start_after(last_doc)

            # 执行查询（带重试）
            docs = list(query.stream(retry=custom_retry))

            if not docs:
                break  # 没有更多数据

            # 处理当前批次
            batch_start = time.time()
            for doc in docs:
                try:
                    save_document(doc, output_dir)
                    total_count += 1
                    last_doc = doc
                except Exception as e:
                    print(f"⚠️ 文档 {doc.id} 保存失败: {type(e).__name__}: {str(e)}")

            # 打印批次信息
            batch_time = time.time() - batch_start
            print(f"🔄 已处理 {total_count} 个文档 | 本批次耗时: {batch_time:.2f}s")

        except Exception as e:
            print(f"⚠️ 批次查询失败: {type(e).__name__}: {str(e)}")
            time.sleep(5)  # 等待后重试
            continue

    # 最终报告
    total_time = time.time() - start_time
    print(f"\n🎉 下载完成! 共 {total_count} 个文档 | 总耗时: {total_time:.2f}s")
    print(f"文件保存在: {os.path.abspath(output_dir)}")


def save_document(doc, output_dir):
    """安全保存单个文档"""
    doc_data = {"id": doc.id, "data": convert_firestore_types(doc.to_dict())}

    file_path = os.path.join(output_dir, f"{doc.id}.json")

    # 原子写入（避免写入不完整文件）
    temp_path = f"{file_path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(doc_data, f, ensure_ascii=False, indent=2)

    os.replace(temp_path, file_path)
    print(f"✅ 保存: {doc.id}")


def convert_firestore_types(data):
    """递归转换 Firestore 特殊类型"""
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
