import re
path = r'C:\Users\venka\Documents\rtl-gen-aii\component_catalog.py'
text = open(path, 'r', encoding='utf-8').read()
# Remove all non-ASCII characters
text = re.sub(r'[^\x00-\x7F]', '', text)
open(path, 'w', encoding='utf-8').write(text)
print('Done cleaning non-ASCII characters')
