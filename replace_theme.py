import os
import glob
import re

app_dir = "/Users/kisanpintupatel/Documents/college_management/app"

def replace_in_file(filepath, replacements):
    with open(filepath, 'r') as f:
        content = f.read()
    
    new_content = content
    for old, new in replacements:
        new_content = new_content.replace(old, new)
        
    if new_content != content:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

# Global replacements for all HTML files
html_replacements = [
    # Replace CampusEvents with RAIT Events
    ("CampusEvents", "RAIT Events"),
    # Replace inline gradients and colors
    ("#667eea", "#A6192E"),
    ("#764ba2", "#7c1322"),
    ("#5568d9", "#7c1322"),
    # Address addition for footer
    ("© 2026 RAIT Events</p>", "© 2026 RAIT Events | RAIT, DY Patil University Campus, Nerul, Navi Mumbai</p>"),
    ("© 2026 RAIT Events\n", "© 2026 RAIT Events | RAIT, DY Patil University Campus, Nerul, Navi Mumbai\n")
]

# CSS specific replacements
css_replacements = [
    ("#4f46e5", "#A6192E"), # Indigo primary to Maroon primary
    ("#3730a3", "#7c1322"), # Indigo hover to Maroon hover
    ("#eef2ff", "#fff0f2"), # Indigo light to Maroon light
    ("#667eea", "#A6192E"), 
    ("CampusEvents", "RAIT Events")
]

# Process HTML files
html_files = glob.glob(os.path.join(app_dir, "templates", "*.html"))
for html_file in html_files:
    replace_in_file(html_file, html_replacements)

# Process CSS files
css_files = glob.glob(os.path.join(app_dir, "static", "css", "*.css"))
for css_file in css_files:
    replace_in_file(css_file, css_replacements)

# Process main.py just in case
replace_in_file(os.path.join(app_dir, "..", "main.py"), [("CampusEvents", "RAIT Events")])

print("Done updating theme.")
