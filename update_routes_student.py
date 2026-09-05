import re

file_path = "/Users/kisanpintupatel/Documents/college_management/main.py"

with open(file_path, "r") as f:
    content = f.read()

routes_to_protect = [
    r'@app\.route\("/student-dashboard"\)',
    r'@app\.route\("/my-events"\)',
    r'@app\.route\("/register/<int:event_id>"\)',
    r'@app\.route\("/cancel-registration/<int:registration_id>"\)',
]

for route in routes_to_protect:
    pattern = re.compile(f'^({route})$', re.MULTILINE)
    if not re.search(f'^({route})\\n@student_required', content, re.MULTILINE):
        content = pattern.sub(r'\1\n@student_required', content)

with open(file_path, "w") as f:
    f.write(content)
