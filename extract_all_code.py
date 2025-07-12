import os

# 支持的文件类型
TARGET_EXTENSIONS = ['.py', '.html', '.txt']

def list_target_files(base_path, self_filename):
    code_structure = []
    file_paths = []

    for root, dirs, files in os.walk(base_path):
        relative_root = os.path.relpath(root, base_path)
        target_files = [
            f for f in files
            if os.path.splitext(f)[1] in TARGET_EXTENSIONS and f != self_filename
        ]
        if not target_files:
            continue

        level = root.replace(base_path, '').count(os.sep)
        indent = '    ' * level
        code_structure.append(f"{indent}{os.path.basename(root)}/")

        subindent = '    ' * (level + 1)
        for file in sorted(target_files):
            relative_path = os.path.relpath(os.path.join(root, file), base_path)
            code_structure.append(f"{subindent}{file}")
            file_paths.append(relative_path)

    return code_structure, file_paths

def read_file_content(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    base_path = os.getcwd()
    self_filename = os.path.basename(__file__)  # 当前脚本的文件名
    output_file = os.path.join(base_path, 'code_structure_and_content.txt')

    code_structure, target_files = list_target_files(base_path, self_filename)

    with open(output_file, 'w', encoding='utf-8') as out:
        out.write("### 目录结构（仅含 .py / .html / .txt 文件）###\n\n")
        for line in code_structure:
            out.write(line + '\n')

        out.write("\n\n### 文件内容 ###\n\n")

        for file_path in target_files:
            out.write(f"# 文件路径: ./{file_path}\n")
            try:
                content = read_file_content(file_path)
                out.write(content + '\n\n')
            except Exception as e:
                out.write(f"# 无法读取 {file_path}：{e}\n\n")

    print(f"✅ 导出完成：{output_file}（自身文件已排除）")

if __name__ == "__main__":
    main()
