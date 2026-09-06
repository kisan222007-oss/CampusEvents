import re

with open("main.py", "r") as f:
    content = f.read()

# Replace class="fa-..." with class='fa-...'
# We can use regex to safely do this
content = re.sub(r'class="fa-solid([^"]+)"', r"class='fa-solid\1'", content)

with open("main.py", "w") as f:
    f.write(content)

print("Fixed quotes in main.py")
