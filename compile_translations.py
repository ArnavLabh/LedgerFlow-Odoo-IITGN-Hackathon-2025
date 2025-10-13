import os
import subprocess

# List of languages to compile
languages = ['en', 'fr', 'de', 'hi', 'gu']

for lang in languages:
    po_file = f'translations/{lang}/LC_MESSAGES/messages.po'
    mo_file = f'translations/{lang}/LC_MESSAGES/messages.mo'
    
    if os.path.exists(po_file):
        print(f'Compiling {lang}...')
        try:
            # Try using pybabel compile
            result = subprocess.run(['pybabel', 'compile', '-f', '-i', po_file, '-o', mo_file], 
                                 capture_output=True, text=True)
            if result.returncode == 0:
                print(f'  ✓ Successfully compiled {lang}')
            else:
                print(f'  ✗ Error compiling {lang}: {result.stderr}')
        except FileNotFoundError:
            # If pybabel is not in PATH, try python -m babel.messages.frontend
            try:
                result = subprocess.run(['python', '-m', 'babel.messages.frontend', 'compile', '-f', '-i', po_file, '-o', mo_file], 
                                     capture_output=True, text=True)
                if result.returncode == 0:
                    print(f'  ✓ Successfully compiled {lang}')
                else:
                    print(f'  ✗ Error compiling {lang}: {result.stderr}')
            except Exception as e:
                print(f'  ✗ Could not compile {lang}: {e}')
    else:
        print(f'  ! {po_file} not found')

print('\nTranslation compilation complete!')