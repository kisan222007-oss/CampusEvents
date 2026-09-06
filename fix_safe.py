import os
import glob

app_dir = "/Users/kisanpintupatel/Documents/college_management/app/templates"
files_to_check = glob.glob(os.path.join(app_dir, "*.html"))

for filepath in files_to_check:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "{{ message }}" in content:
        content = content.replace("{{ message }}", "{{ message | safe }}")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

print("Done updating safe filters.")
