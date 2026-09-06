import os
import glob
import re

app_dir = "/Users/kisanpintupatel/Documents/college_management/app"
fa_cdn = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">\n</head>'

emoji_map = {
    "🎓": '<i class="fa-solid fa-graduation-cap"></i>',
    "🎉": '<i class="fa-solid fa-calendar-check"></i>',
    "🚪": '<i class="fa-solid fa-right-from-bracket"></i>',
    "🎟️": '<i class="fa-solid fa-ticket"></i>',
    "📊": '<i class="fa-solid fa-chart-column"></i>',
    "👥": '<i class="fa-solid fa-users"></i>',
    "🔎": '<i class="fa-solid fa-magnifying-glass"></i>',
    "🔐": '<i class="fa-solid fa-lock"></i>',
    "👤": '<i class="fa-solid fa-user"></i>',
    "📱": '<i class="fa-solid fa-mobile-screen"></i>',
    "📧": '<i class="fa-solid fa-envelope"></i>',
    "💾": '<i class="fa-solid fa-floppy-disk"></i>',
    "📅": '<i class="fa-solid fa-calendar"></i>',
    "⏰": '<i class="fa-solid fa-clock"></i>',
    "📍": '<i class="fa-solid fa-location-dot"></i>',
    "📋": '<i class="fa-solid fa-clipboard-list"></i>',
    "📝": '<i class="fa-solid fa-pen-to-square"></i>',
    "✅": '<i class="fa-solid fa-circle-check"></i>',
    "❌": '<i class="fa-solid fa-circle-xmark"></i>',
    "⚠️": '<i class="fa-solid fa-triangle-exclamation"></i>'
}

def replace_emojis(content):
    for emoji, icon in emoji_map.items():
        content = content.replace(emoji, icon)
    return content

html_files = glob.glob(os.path.join(app_dir, "templates", "*.html"))
for filepath in html_files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Inject FontAwesome if not exists
    if "font-awesome" not in content and "</head>" in content:
        content = content.replace("</head>", fa_cdn)
        
    # Replace Emojis
    content = replace_emojis(content)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

# Update main.py for emojis in flash messages
main_py_path = os.path.join(app_dir, "..", "main.py")
with open(main_py_path, 'r', encoding='utf-8') as f:
    main_content = f.read()

main_content = replace_emojis(main_content)
with open(main_py_path, 'w', encoding='utf-8') as f:
    f.write(main_content)

print("Done updating emojis and injecting FontAwesome.")
