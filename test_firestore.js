const admin = require('firebase-admin');
const serviceAccount = require('./config/serviceAccount.json');

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
});

const db = admin.firestore();

(async () => {
  try {
    const docRef = await db.collection('test-connection').add({
      timestamp: new Date(),
      message: 'Test OK'
    });

    console.log('✅ Firestore 测试成功，文档ID:', docRef.id);
  } catch (err) {
    console.error('❌ Firestore 连接失败:', err.message);
  }
})();
