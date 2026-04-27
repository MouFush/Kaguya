#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据加密和隐私保护系统
参考: AWS KMS, HashiCorp Vault
"""

import os
import json
import base64
import hashlib
import secrets
from typing import Dict, Optional, Union
from dataclasses import dataclass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import sqlite3
import threading

# 密钥存储目录
KEYS_DIR = os.path.join(os.path.dirname(__file__), 'encryption_keys')
os.makedirs(KEYS_DIR, exist_ok=True)

@dataclass
class EncryptedData:
    """加密数据结构"""
    ciphertext: str
    salt: str
    iv: str
    version: int = 1
    
    def to_dict(self) -> Dict:
        return {
            'ciphertext': self.ciphertext,
            'salt': self.salt,
            'iv': self.iv,
            'version': self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EncryptedData':
        return cls(
            ciphertext=data['ciphertext'],
            salt=data['salt'],
            iv=data['iv'],
            version=data.get('version', 1)
        )

class KeyManager:
    """密钥管理器"""
    
    def __init__(self):
        self.db_path = os.path.join(KEYS_DIR, 'keys.db')
        self._init_database()
        self._master_key = self._get_or_create_master_key()
        self._cache = {}
        self._lock = threading.Lock()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS encryption_keys (
                id TEXT PRIMARY KEY,
                key_type TEXT NOT NULL,
                key_data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _get_or_create_master_key(self) -> bytes:
        """获取或创建主密钥"""
        master_key_file = os.path.join(KEYS_DIR, 'master.key')
        
        if os.path.exists(master_key_file):
            with open(master_key_file, 'rb') as f:
                return base64.urlsafe_b64decode(f.read())
        else:
            # 生成新主密钥
            key = Fernet.generate_key()
            with open(master_key_file, 'wb') as f:
                f.write(base64.urlsafe_b64encode(key))
            # 设置文件权限（仅所有者可读写）
            os.chmod(master_key_file, 0o600)
            return key
    
    def create_data_key(self, key_id: str) -> bytes:
        """创建数据加密密钥"""
        key = Fernet.generate_key()
        
        # 使用主密钥加密数据密钥
        f = Fernet(self._master_key)
        encrypted_key = f.encrypt(key)
        
        # 保存到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO encryption_keys (id, key_type, key_data, created_at)
            VALUES (?, ?, ?, datetime('now'))
        ''', (key_id, 'data_key', base64.urlsafe_b64encode(encrypted_key).decode()))
        conn.commit()
        conn.close()
        
        return key
    
    def get_data_key(self, key_id: str) -> Optional[bytes]:
        """获取数据加密密钥"""
        # 检查缓存
        if key_id in self._cache:
            return self._cache[key_id]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT key_data FROM encryption_keys 
            WHERE id = ? AND is_active = 1
        ''', (key_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # 解密数据密钥
        encrypted_key = base64.urlsafe_b64decode(row[0].encode())
        f = Fernet(self._master_key)
        key = f.decrypt(encrypted_key)
        
        # 缓存
        with self._lock:
            self._cache[key_id] = key
        
        return key
    
    def rotate_key(self, key_id: str) -> bool:
        """轮换密钥"""
        # 创建新密钥
        new_key = self.create_data_key(f"{key_id}_new")
        
        # 标记旧密钥为过期
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE encryption_keys 
            SET expires_at = datetime('now'), is_active = 0
            WHERE id = ?
        ''', (key_id,))
        
        # 重命名新密钥
        cursor.execute('''
            UPDATE encryption_keys SET id = ? WHERE id = ?
        ''', (key_id, f"{key_id}_new"))
        
        conn.commit()
        conn.close()
        
        # 清除缓存
        with self._lock:
            self._cache.pop(key_id, None)
        
        return True

class EncryptionService:
    """加密服务"""
    
    def __init__(self):
        self.key_manager = KeyManager()
    
    def encrypt(self, plaintext: Union[str, bytes], 
                key_id: str = "default") -> EncryptedData:
        """加密数据"""
        # 获取或创建数据密钥
        key = self.key_manager.get_data_key(key_id)
        if not key:
            key = self.key_manager.create_data_key(key_id)
        
        # 生成随机盐值
        salt = secrets.token_hex(16)
        
        # 使用PBKDF2派生密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
            backend=default_backend()
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key))
        
        # 加密数据
        f = Fernet(derived_key)
        
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        
        ciphertext = f.encrypt(plaintext)
        
        return EncryptedData(
            ciphertext=base64.urlsafe_b64encode(ciphertext).decode(),
            salt=salt,
            iv="",  # Fernet内部处理IV
            version=1
        )
    
    def decrypt(self, encrypted_data: EncryptedData, 
                key_id: str = "default") -> str:
        """解密数据"""
        # 获取数据密钥
        key = self.key_manager.get_data_key(key_id)
        if not key:
            raise ValueError(f"Key not found: {key_id}")
        
        # 使用PBKDF2派生密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=encrypted_data.salt.encode(),
            iterations=100000,
            backend=default_backend()
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key))
        
        # 解密数据
        f = Fernet(derived_key)
        ciphertext = base64.urlsafe_b64decode(encrypted_data.ciphertext.encode())
        plaintext = f.decrypt(ciphertext)
        
        return plaintext.decode('utf-8')
    
    def encrypt_field(self, value: str, field_name: str, 
                     tenant_id: Optional[str] = None) -> str:
        """加密字段（返回JSON字符串）"""
        key_id = f"{tenant_id or 'global'}_{field_name}"
        encrypted = self.encrypt(value, key_id)
        return json.dumps(encrypted.to_dict())
    
    def decrypt_field(self, encrypted_json: str, field_name: str,
                     tenant_id: Optional[str] = None) -> str:
        """解密字段"""
        key_id = f"{tenant_id or 'global'}_{field_name}"
        data = json.loads(encrypted_json)
        encrypted = EncryptedData.from_dict(data)
        return self.decrypt(encrypted, key_id)
    
    def hash_sensitive_data(self, data: str, 
                           salt: Optional[str] = None) -> str:
        """哈希敏感数据（用于搜索）"""
        if not salt:
            salt = secrets.token_hex(16)
        
        hash_value = hashlib.pbkdf2_hmac(
            'sha256',
            data.encode(),
            salt.encode(),
            100000
        )
        
        return f"{salt}${base64.urlsafe_b64encode(hash_value).decode()}"
    
    def verify_hash(self, data: str, hashed: str) -> bool:
        """验证哈希"""
        try:
            salt, _ = hashed.split('$', 1)
            new_hash = self.hash_sensitive_data(data, salt)
            return new_hash == hashed
        except:
            return False

class PrivacyProtector:
    """隐私保护器"""
    
    def __init__(self):
        self.encryption = EncryptionService()
    
    def mask_pii(self, text: str) -> str:
        """掩码PII信息"""
        import re
        
        masked = text
        
        # 手机号掩码
        masked = re.sub(r'(\d{3})\d{4}(\d{4})', r'\1****\2', masked)
        
        # 邮箱掩码
        masked = re.sub(r'([a-zA-Z0-9._%+-])[a-zA-Z0-9._%+-]*(@[a-zA-Z0-9.-]+)', 
                       r'\1***\2', masked)
        
        # 身份证号掩码
        masked = re.sub(r'(\d{6})\d{8}(\d{4})', r'\1********\2', masked)
        
        return masked
    
    def anonymize_data(self, data: Dict, fields: list) -> Dict:
        """匿名化数据"""
        result = data.copy()
        
        for field in fields:
            if field in result:
                # 使用哈希替换敏感值
                value = str(result[field])
                result[field] = hashlib.sha256(value.encode()).hexdigest()[:16]
        
        return result
    
    def pseudonymize(self, identifier: str) -> str:
        """假名化处理"""
        return hashlib.sha256(identifier.encode()).hexdigest()[:16]

# 全局实例
encryption_service = EncryptionService()
privacy_protector = PrivacyProtector()

if __name__ == '__main__':
    # 测试
    service = EncryptionService()
    
    # 测试加密解密
    plaintext = "这是一段敏感数据：13800138000"
    print(f"原始数据: {plaintext}")
    
    encrypted = service.encrypt(plaintext)
    print(f"加密后: {encrypted.to_dict()}")
    
    decrypted = service.decrypt(encrypted)
    print(f"解密后: {decrypted}")
    
    # 测试字段加密
    field_encrypted = service.encrypt_field("敏感字段值", "email", "tenant_123")
    print(f"\n字段加密: {field_encrypted}")
    
    field_decrypted = service.decrypt_field(field_encrypted, "email", "tenant_123")
    print(f"字段解密: {field_decrypted}")
    
    # 测试哈希
    hashed = service.hash_sensitive_data("13800138000")
    print(f"\n哈希值: {hashed}")
    print(f"验证: {service.verify_hash('13800138000', hashed)}")
    
    # 测试隐私保护
    protector = PrivacyProtector()
    text = "联系邮箱：user@example.com，电话：13800138000"
    print(f"\n原始文本: {text}")
    print(f"掩码后: {protector.mask_pii(text)}")
