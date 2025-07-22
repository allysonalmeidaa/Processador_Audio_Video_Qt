# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import copy_metadata

yt_dlp_cacert = None
try:
    import yt_dlp
    yt_dlp_path = os.path.dirname(yt_dlp.__file__)
    cacert_path = os.path.join(yt_dlp_path, "cacert.pem")
    if os.path.exists(cacert_path):
        yt_dlp_cacert = (cacert_path, 'yt_dlp/')
except Exception:
    yt_dlp_cacert = None

datas_yt_dlp = copy_metadata('yt-dlp')

datas = [
    ('config.json', '.'),
    ('historico.json', '.'),
    ('saida_audio', 'saida_audio'),
    ('Transcricoes', 'Transcricoes'),
    ('microphone2.png', '.'),
    ('resemblyzer', 'resemblyzer'),
    ('.venv-novo/Lib/site-packages/whisper/assets/mel_filters.npz', 'whisper/assets'),
    ('.venv-novo/Lib/site-packages/whisper/assets/multilingual.tiktoken', 'whisper/assets'),
    ('erros_usuarios.json', '.'),
    # NÃO inclua .cache/whisper!
    # ('ffmpeg.exe', '.'),   # Descomente se quiser embutir ffmpeg
]

if yt_dlp_cacert:
    datas.append(yt_dlp_cacert)

datas += datas_yt_dlp

a = Analysis(
    ['Transcricao_main_V3.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'yt_dlp',
        'yt_dlp.utils',
        'yt_dlp.extractor',
        'yt_dlp.postprocessor',
        'torch',
        'whisper',
        # sklearn e dependências compiladas:
        'sklearn._cyutility',
        'sklearn.utils._cython_blas',
        'sklearn.utils._weight_vector',
        'sklearn.utils._openmp_helpers',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Processador de Áudio e Vídeo (Qt)',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Não compacte! Minimiza falso positivo de antivírus
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Para produção. Use True para debug em terminal.
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
