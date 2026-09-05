import re

file_path = "/Users/kisanpintupatel/Documents/college_management/main.py"

with open(file_path, "r") as f:
    content = f.read()

routes_to_protect = [
    r'@app\.route\("/admin/organizers"\)',
    r'@app\.route\("/admin/organizers/approve/<int:request_id>"\)',
    r'@app\.route\("/admin/organizers/reject/<int:request_id>"\)',
    r'@app\.route\("/admin/organizers/delete/<int:organizer_id>"\)',
    r'@app\.route\("/admin/organizers/toggle-status/<int:organizer_id>"\)',
]

for route in routes_to_protect:
    pattern = re.compile(f'^({route})$', re.MULTILINE)
    if not re.search(f'^({route})\\n@main_admin_required', content, re.MULTILINE):
        content = pattern.sub(r'\1\n@main_admin_required', content)

with open(file_path, "w") as f:
    f.write(content)
