import os
import zipfile
import xml.etree.ElementTree as ET

# Path to the Excel file
excel_file = r"C:\Users\SekharUprety\OneDrive - Action Builders\Desktop\Scope-Project_ AB 2\project files\fomat final selection .xlsx"

# Excel files are ZIP archives - let's explore them
try:
    with zipfile.ZipFile(excel_file, 'r') as zip_ref:
        print("=== Files in Excel archive ===")
        for name in zip_ref.namelist():
            print(name)
        
        # Try to read sharedStrings.xml which contains text content
        if 'xl/sharedStrings.xml' in zip_ref.namelist():
            print("\n=== Shared Strings (text content) ===")
            with zip_ref.open('xl/sharedStrings.xml') as f:
                content = f.read().decode('utf-8')
                # Parse XML
                root = ET.fromstring(content)
                ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                strings = root.findall('.//main:si', ns)
                for i, s in enumerate(strings[:50]):  # First 50 strings
                    # Get text from <t> elements
                    text = ''.join(t.text for t in s.findall('.//main:t', ns) if t.text)
                    print(f"{i+1}: {text}")
except Exception as e:
    print(f"Error: {e}")
