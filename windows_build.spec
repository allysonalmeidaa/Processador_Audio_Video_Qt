# -*- mode: python ; coding: utf-8 -*-
 
block_cipher = None
 
# Lista de dados - use caminhos relativos
datas = [
    # Arquivos principais
    ('config.json', '.'),
    ('historico.json', '.'),
    ('microphone2.png', '.'),
    ('erros_usuarios.json', '.'),
    # Novos arquivos
    ('whisper_worker.py', '.'),
    ('diarizacao_resemblyzer.py', '.'),
    ('memory_utils.py', '.'),
    # Arquivos do resemblyzer
    ('resemblyzer/pretrained.pt', 'resemblyzer'),
]
 
# Adicionar assets do whisper manualmente (ajuste os caminhos conforme necessário)
try:
    import whisper
    whisper_path = os.path.dirname(whisper.__file__)
    datas.append((os.path.join(whisper_path, 'assets', 'mel_filters.npz'), 'whisper/assets'))
    datas.append((os.path.join(whisper_path, 'assets', 'multilingual.tiktoken'), 'whisper/assets'))
    datas.append((os.path.join(whisper_path, 'assets', 'gpt2.tiktoken'), 'whisper/assets'))
except:
    pass
 
a = Analysis(
    ['Transcricao_main_V3.py'],
    pathex=[],  # Deixe vazio, PyInstaller encontra automaticamente
    binaries=[],
    datas=datas,
    hiddenimports=[
        # Core
        'torch', 'whisper', 'librosa', 'numpy',
        # Diarização
        'sklearn.cluster', 'sklearn.utils._typedefs',
        # Audio processing
        'soundfile', 'resampy', 
        # PyQt
        'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
        # Nossos módulos
        'Transcricao_tab_V3', 'logs_tab', 'ffmpeg_utils',
        'whisper_worker', 'diarizacao_resemblyzer', 'memory_utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'typing',
        'tkinter', 'matplotlib', 'pytest', 'unittest',
        'jupyter', 'ipython', 'dask', 'bokeh',
    ],
    noarchive=False,
    optimize=1,
)
 
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
 
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Processador_Audio_Video',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
 
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Processador_Audio_Video',
)