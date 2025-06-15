const admin = require('firebase-admin');
const path = require('path');
const fs = require('fs');

// 初始化 Firebase Admin
const serviceAccount = require('./config/serviceAccount.json');

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  storageBucket: 'portfolio-d5d1f.appspot.com'
});

const db = admin.firestore();
const bucket = admin.storage().bucket();

/**
 * 使用 firebase-admin 上传文件
 */
async function uploadFile(filePath, tag) {
  const fileName = path.basename(filePath);
  const storageDest = `${Date.now()}_${fileName}`;
  const collectionRef = db.collection('images');

  console.log(`开始上传: ${fileName}`);

  try {
    // 上传文件
    await bucket.upload(filePath, {
      destination: storageDest,
      metadata: {
        contentType: 'image/jpeg',
        metadata: { tag }
      }
    });

    // 获取下载链接
    const file = bucket.file(storageDest);
    const [url] = await file.getSignedUrl({
      action: 'read',
      expires: Date.now() + 1000 * 60 * 60 * 24 * 7 // 7天有效
    });

    // 添加文档到 Firestore
    const docRef = await collectionRef.add({
      name: fileName,
      url,
      tag,
      createdAt: admin.firestore.FieldValue.serverTimestamp()
    });

    console.log(`${fileName} 上传完成，文档ID: ${docRef.id}`);
    return { id: docRef.id, name: fileName, url, tag };

  } catch (error) {
    console.error(`${fileName} 上传失败:`, error.message);
    throw error;
  }
}

/**
 * 处理压缩文件夹
 */
async function processCompressedFolder() {
  const compressedDir = path.join('output', 'compressed');

  if (!fs.existsSync(compressedDir)) {
    throw new Error(`压缩文件夹不存在: ${compressedDir}`);
  }

  const metadataPath = path.join(compressedDir, 'image_data.json');
  const existingMetadata = fs.existsSync(metadataPath) ?
    JSON.parse(fs.readFileSync(metadataPath, 'utf8')) : [];

  const metadataMap = new Map(existingMetadata.map(item => [item.name, item]));

  const subDirs = fs.readdirSync(compressedDir, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory())
    .map(dirent => dirent.name);

  const results = [];

  for (const dir of subDirs) {
    const dirPath = path.join(compressedDir, dir);
    const files = fs.readdirSync(dirPath)
      .filter(file => ['.jpg', '.jpeg', '.png', '.webp'].includes(path.extname(file).toLowerCase()));

    for (const file of files) {
      const filePath = path.join(dirPath, file);
      const existingData = metadataMap.get(file);
      const tag = existingData?.tag || dir;

      try {
        console.log(`\n处理文件: ${file}`);
        const result = await uploadFile(filePath, tag);
        results.push(result);

        // 避免速率限制
        await new Promise(r => setTimeout(r, 1000));
      } catch (error) {
        results.push({ file, error: error.message });
      }
    }
  }

  const resultPath = path.join(compressedDir, 'upload_results.json');
  fs.writeFileSync(resultPath, JSON.stringify(results, null, 2));
  console.log(`上传完成，结果保存在: ${resultPath}`);
  return results;
}

// 启动执行
(async () => {
  try {
    console.log('开始上传流程...');
    const start = Date.now();

    const results = await processCompressedFolder();
    const success = results.filter(r => !r.error).length;
    const fail = results.length - success;
    const elapsed = ((Date.now() - start) / 1000).toFixed(1);

    console.log(`
      ✅ 上传结束
      耗时: ${elapsed} 秒
      成功: ${success}
      失败: ${fail}
    `);

    if (fail > 0) {
      console.log('\n❌ 失败文件:');
      results.filter(r => r.error).forEach(r => {
        console.log(`- ${r.file}: ${r.error}`);
      });
    }

  } catch (error) {
    console.error('处理流程出错:', error);
    process.exit(1);
  }
})();
