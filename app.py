from flask import Flask, render_template, request, jsonify
import subprocess
import sys
import os
import tempfile
import json
import time
from threading import Timer
import shutil

app = Flask(__name__)

# Güvenlik için maksimum çalışma süresi (saniye)
MAX_EXECUTION_TIME = 10

class CodeExecutor:
    def __init__(self):
        self.process = None
        self.output = ""
        self.error = ""
        self.timed_out = False
    
    def timeout_handler(self):
        """Kod çalışma süresini kontrol et"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.timed_out = True
    
    def execute_python_code(self, code):
        """Python kodunu güvenli bir şekilde çalıştır"""
        try:
            # UTF-8 encoding desteği için kodun başına encoding bildirimi ekle
            encoded_code = "# -*- coding: utf-8 -*-\n" + code
            
            # Geçici dosya oluştur - UTF-8 encoding ile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(encoded_code)
                temp_file_path = temp_file.name
            
            # Timer başlat
            timer = Timer(MAX_EXECUTION_TIME, self.timeout_handler)
            timer.start()
            
            # Kodu çalıştır - UTF-8 environment variable'ı ekle
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            self.process = subprocess.Popen(
                [sys.executable, temp_file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=tempfile.gettempdir(),
                env=env,
                encoding='utf-8'
            )
            
            # Çıktıyı al
            stdout, stderr = self.process.communicate()
            timer.cancel()
            
            # Geçici dosyayı temizle
            os.unlink(temp_file_path)
            
            if self.timed_out:
                return {
                    'success': False,
                    'output': '',
                    'error': f'Kod çalışma süresi {MAX_EXECUTION_TIME} saniyeyi aştı!'
                }
            
            return {
                'success': self.process.returncode == 0,
                'output': stdout,
                'error': stderr
            }
            
        except Exception as e:
            # Geçici dosyayı temizle (hata durumunda)
            try:
                if 'temp_file_path' in locals():
                    os.unlink(temp_file_path)
            except:
                pass
            
            return {
                'success': False,
                'output': '',
                'error': str(e)
            }

class PackageManager:
    def __init__(self):
        self.installed_packages = set()
    
    def install_package(self, package_name):
        """Paket yükleme simülasyonu (gerçek projede pip kullanılabilir)"""
        try:
            # Güvenlik için sadece belirli paketlere izin ver
            allowed_packages = [
                'requests', 'numpy', 'pandas', 'matplotlib', 'json', 'datetime',
                'math', 'random', 'os', 'sys', 'time', 'collections', 'itertools',
                'functools', 'operator', 'string', 'textwrap', 'unicodedata',
                'statistics', 'decimal', 'fractions', 'base64', 'hashlib',
                'hmac', 'secrets', 'uuid', 'urllib', 'http', 'json', 'csv',
                'configparser', 'logging', 'pickle', 'sqlite3', 'threading',
                'multiprocessing', 'subprocess', 'queue', 'socket', 'ssl',
                'email', 'calendar', 'locale', 'gettext', 'argparse', 'shlex',
                'glob', 'fnmatch', 'linecache', 'shutil', 'tempfile', 'gzip',
                'bz2', 'lzma', 'zipfile', 'tarfile', 'pathlib', 'io', 'codecs'
            ]
            
            if package_name not in allowed_packages:
                return {
                    'success': False,
                    'message': f'Paket "{package_name}" yüklenmesine izin verilmiyor. İzin verilen paketler: {", ".join(allowed_packages[:10])}...'
                }
            
            # Paket zaten yüklü mü kontrol et
            if package_name in self.installed_packages:
                return {
                    'success': True,
                    'message': f'Paket "{package_name}" zaten yüklü.'
                }
            
            # Basit paketler için (built-in modüller) direkt ekleme
            builtin_modules = [
                'math', 'random', 'os', 'sys', 'time', 'collections', 'itertools',
                'functools', 'operator', 'string', 'textwrap', 'unicodedata',
                'statistics', 'decimal', 'fractions', 'base64', 'hashlib',
                'hmac', 'secrets', 'uuid', 'urllib', 'http', 'json', 'csv',
                'configparser', 'logging', 'pickle', 'sqlite3', 'threading',
                'multiprocessing', 'subprocess', 'queue', 'socket', 'ssl',
                'email', 'calendar', 'locale', 'gettext', 'argparse', 'shlex',
                'glob', 'fnmatch', 'linecache', 'shutil', 'tempfile', 'gzip',
                'bz2', 'lzma', 'zipfile', 'tarfile', 'pathlib', 'io', 'codecs'
            ]
            
            if package_name in builtin_modules:
                self.installed_packages.add(package_name)
                return {
                    'success': True,
                    'message': f'Built-in modül "{package_name}" kullanıma hazır.'
                }
            
            # Gerçek pip install (dikkatli kullan!)
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', package_name],
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                self.installed_packages.add(package_name)
                return {
                    'success': True,
                    'message': f'Paket "{package_name}" başarıyla yüklendi.'
                }
            else:
                return {
                    'success': False,
                    'message': f'Paket yükleme hatası: {result.stderr}'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'message': 'Paket yükleme işlemi zaman aşımına uğradı.'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Hata: {str(e)}'
            }

# Global nesneler
code_executor = CodeExecutor()
package_manager = PackageManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/execute', methods=['POST'])
def execute_code():
    """Python kodunu çalıştır"""
    data = request.get_json()
    code = data.get('code', '')
    
    if not code.strip():
        return jsonify({
            'success': False,
            'output': '',
            'error': 'Kod boş olamaz!'
        })
    
    result = code_executor.execute_python_code(code)
    return jsonify(result)

@app.route('/install', methods=['POST'])
def install_package():
    """Paket yükle"""
    data = request.get_json()
    package_name = data.get('package', '')
    
    if not package_name.strip():
        return jsonify({
            'success': False,
            'message': 'Paket adı boş olamaz!'
        })
    
    result = package_manager.install_package(package_name)
    return jsonify(result)

@app.route('/packages')
def list_packages():
    """Yüklü paketleri listele"""
    return jsonify({
        'installed': list(package_manager.installed_packages)
    })

@app.route('/examples')
def get_examples():
    """Örnek kodlar"""
    examples = [
        {
            'title': 'Merhaba Dünya',
            'code': 'print("Merhaba Dünya!")\nprint("Python Compiler çalışıyor!")\nprint("Türkçe karakterler: ü, ö, ç, ş, ı, ğ")'
        },
        {
            'title': 'Matematik İşlemleri',
            'code': 'import math\n\n# Temel işlemler\na = 10\nb = 5\nprint(f"Toplama: {a + b}")\nprint(f"Çıkarma: {a - b}")\nprint(f"Çarpma: {a * b}")\nprint(f"Bölme: {a / b}")\n\n# Matematik fonksiyonları\nprint(f"Karekök: {math.sqrt(16)}")\nprint(f"Üs alma: {math.pow(2, 3)}")\nprint(f"Pi sayısı: {math.pi}")'
        },
        {
            'title': 'Liste İşlemleri',
            'code': '# Liste oluşturma\nsayılar = [1, 2, 3, 4, 5]\nprint(f"Liste: {sayılar}")\n\n# Liste işlemleri\nprint(f"Toplam: {sum(sayılar)}")\nprint(f"Maximum: {max(sayılar)}")\nprint(f"Minimum: {min(sayılar)}")\nprint(f"Ortalama: {sum(sayılar) / len(sayılar)}")\n\n# List comprehension\nkareler = [x**2 for x in sayılar]\nprint(f"Kareler: {kareler}")\n\n# Çift sayılar\nçift_sayılar = [x for x in sayılar if x % 2 == 0]\nprint(f"Çift sayılar: {çift_sayılar}")'
        },
        {
            'title': 'String İşlemleri',
            'code': '# String tanımlama\nisim = "Ahmet"\nsoyisim = "Yılmaz"\n\n# String birleştirme\ntam_isim = isim + " " + soyisim\nprint(f"Tam isim: {tam_isim}")\n\n# String metotları\nprint(f"Büyük harf: {tam_isim.upper()}")\nprint(f"Küçük harf: {tam_isim.lower()}")\nprint(f"Başlık: {tam_isim.title()}")\nprint(f"Uzunluk: {len(tam_isim)}")\n\n# String slicing\nprint(f"İlk 5 karakter: {tam_isim[:5]}")\nprint(f"Son 5 karakter: {tam_isim[-5:]}")'
        },
        {
            'title': 'Fonksiyonlar',
            'code': '# Basit fonksiyon\ndef selamla(isim):\n    return f"Merhaba {isim}!"\n\n# Fonksiyonu çağır\nprint(selamla("Dünya"))\nprint(selamla("Python"))\n\n# Parametreli fonksiyon\ndef toplama(a, b):\n    return a + b\n\n# Fonksiyonu test et\nsonuç = toplama(5, 3)\nprint(f"5 + 3 = {sonuç}")\n\n# Faktöriyel hesaplama\ndef faktöriyel(n):\n    if n <= 1:\n        return 1\n    return n * faktöriyel(n - 1)\n\nprint(f"5! = {faktöriyel(5)}")'
        },
        {
            'title': 'Döngüler',
            'code': '# For döngüsü\nprint("For döngüsü:")\nfor i in range(1, 6):\n    print(f"Sayı: {i}")\n\nprint("\\nListe üzerinde döngü:")\nmeyveler = ["elma", "armut", "muz", "üzüm"]\nfor meyve in meyveler:\n    print(f"Meyve: {meyve}")\n\n# While döngüsü\nprint("\\nWhile döngüsü:")\nsayaç = 1\nwhile sayaç <= 5:\n    print(f"Sayaç: {sayaç}")\n    sayaç += 1\n\n# Enumerate kullanımı\nprint("\\nEnumerate ile:")\nfor indeks, meyve in enumerate(meyveler):\n    print(f"{indeks + 1}. {meyve}")'
        },
        {
            'title': 'Sözlük (Dictionary) İşlemleri',
            'code': '# Sözlük oluşturma\nöğrenci = {\n    "isim": "Ali",\n    "yaş": 20,\n    "bölüm": "Bilgisayar Mühendisliği",\n    "notlar": [85, 92, 78, 95]\n}\n\n# Sözlük elemanlarına erişim\nprint(f"İsim: {öğrenci[\'isim\']}")\nprint(f"Yaş: {öğrenci[\'yaş\']}")\nprint(f"Bölüm: {öğrenci[\'bölüm\']}")\n\n# Notların ortalaması\nortalama = sum(öğrenci["notlar"]) / len(öğrenci["notlar"])\nprint(f"Not ortalaması: {ortalama:.2f}")\n\n# Sözlük metotları\nprint(f"Anahtarlar: {list(öğrenci.keys())}")\nprint(f"Değerler: {list(öğrenci.values())}")\n\n# Yeni eleman ekleme\nöğrenci["şehir"] = "İstanbul"\nprint(f"Güncellenmiş öğrenci: {öğrenci}")'
        }
    ]
    return jsonify(examples)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)