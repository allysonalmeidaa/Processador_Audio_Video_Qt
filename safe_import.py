import builtins
 
_original_import = builtins.__import__
 
def safe_import(name, globals=None, locals=None, fromlist=(), level=0):

    """Import seguro que evita bibliotecas problemáticas durante UI"""

    whitelist = ['whisper', 'torch', 'numpy', 'scipy', 'resemblyzer', 'librosa']

    if any(name.startswith(allowed) for allowed in whitelist):
        return _original_import(name, globals, locals, fromlist, level)

    blacklist = ['cv2', 'opencv', 'pygame', 'tkinter']

    if any(name.startswith(blacklisted) for blacklisted in blacklist):

        # Retorna mock para evitar segmentation fault

        class MockModule:

            def __getattr__(self, name):

                return MockModule()

            def __call__(self, *args, **kwargs):

                return MockModule()

            def __bool__(self):

                return False

            def __str__(self):

                return f"MockModule({name})"

        return MockModule()

    return _original_import(name, globals, locals, fromlist, level)
 
# Aplicar import seguro

# builtins.__import__ = safe_import
