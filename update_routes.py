import re

file_path = "/Users/kisanpintupatel/Documents/college_management/main.py"

with open(file_path, "r") as f:
    content = f.read()

routes_to_protect = [
    r'@app\.route\("/admin"\)',
    r'@app\.route\("/admin/registrations"\)',
    r'@app\.route\("/admin/export-registrations"\)',
    r'@app\.route\("/admin/delete-registration/<int:registration_id>"\)',
    r'@app\.route\("/add-event", methods=\["GET", "POST"\]\)',
    r'@app\.route\("/edit-event/<int:event_id>", methods=\["GET", "POST"\]\)',
    r'@app\.route\("/delete-event/<int:event_id>"\)',
    r'@app\.route\("/analysis"\)',
    r'@app\.route\("/search", methods=\["GET", "POST"\]\)',
]

for route in routes_to_protect:
    pattern = re.compile(f'^({route})$', re.MULTILINE)
    # Check if not already followed by @admin_required
    if not re.search(f'^({route})\\n@admin_required', content, re.MULTILINE):
        content = pattern.sub(r'\1\n@admin_required', content)

with open(file_path, "w") as f:
    f.write(content)
