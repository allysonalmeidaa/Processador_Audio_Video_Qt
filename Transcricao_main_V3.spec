# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path
from PyInstaller.utils.hooks import copy_metadata

# Whisper assets
whisper_assets = []
try:
    import whisper
    pkg_dir = Path(whisper.__file__).parent
    assets_dir = pkg_dir / "assets"
    for fname in ("mel_filters.npz", "multilingual.tiktoken"):
        src = assets_dir / fname
        if src.exists():
            whisper_assets.append((str(src), "whisper/assets"))
except Exception:
    pass

yt_dlp_cacert = None
try:
    import yt_dlp
    ydir = os.path.dirname(yt_dlp.__file__)
    cacert_path = os.path.join(ydir, "cacert.pem")
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
    ('erros_usuarios.json', '.'),
]
datas += whisper_assets
if yt_dlp_cacert:
    datas.append(yt_dlp_cacert)
datas += datas_yt_dlp

# Qt minimal plugins
def qt_minimal_plugins():
    import PyQt6
    base = Path(PyQt6.__file__).parent / "Qt6" / "plugins"
    out = []
    plat = base / "platforms" / "qwindows.dll"
    if plat.exists():
        out.append((str(plat), "PyQt6/Qt6/plugins/platforms"))
    for name in ["qico.dll","qjpeg.dll"]:
        p = base / "imageformats" / name
        if p.exists():
            out.append((str(p), "PyQt6/Qt6/plugins/imageformats"))
    style = base / "styles" / "qwindowsvistastyle.dll"
    if style.exists():
        out.append((str(style), "PyQt6/Qt6/plugins/styles"))
    return out
datas += qt_minimal_plugins()

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
        'torch._C',
        'whisper',
        'librosa',
        'soundfile',
        'resampy',
        'webrtcvad',
        'numba',
        'numba.core',
        'numba.core.types',
        'numba.core.typing',
        'llvmlite',
        'llvmlite.binding',
        'sklearn',
        'sklearn.cluster',
        'sklearn.utils._openmp_helpers',
        'sklearn.utils._weight_vector',
        'sklearn.utils._cython_blas',
        'sklearn._cyutility',
        # Adicione outros hiddenimports se necessário
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Qt extras não usados
        'PyQt6.QtWebEngineCore','PyQt6.QtWebEngineWidgets','PyQt6.QtWebEngineQuick',
        'PyQt6.QtWebChannel','PyQt6.QtPositioning','PyQt6.QtLocation','PyQt6.QtQml',
        'PyQt6.QtQuick','PyQt6.QtQuick3D','PyQt6.QtWebSockets','PyQt6.QtNetworkAuth',
        'PyQt6.QtSensors','PyQt6.QtSerialPort','PyQt6.QtTextToSpeech',
        'PyQt6.QtBluetooth','PyQt6.QtNfc'
    ],
    noarchive=False,
    optimize=1,   # <- Corrigido! NÃO use optimize=2!
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Processador_AV',
    debug=,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[
        'torch_cpu.dll','torch.dll','c10.dll','fbgemm.dll','libiomp5md.dll','mkldnn.dll'
    ],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
)