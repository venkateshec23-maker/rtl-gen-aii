# verilog_helpers.py

def add_comment(text):
    return f"// {text}"

def indent_line(line, spaces=4):
    return (" " * spaces) + line

def create_always_block(sensitivity, statements):
    lines = []
    lines.append(f"always {sensitivity} begin")
    for stmt in statements:
        lines.append(indent_line(stmt))
    lines.append("end")
    return "\n".join(lines)
