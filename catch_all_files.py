import os

def read_files(root_dir):
    for subdir, dirs, files in os.walk(root_dir):
        for file in files:
            file_path = os.path.join(subdir, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                content = f"Не удалось прочитать файл: {e}"
            # Выводим комментарий с названием файла перед кодом
            print(f"# {file}\n{content}\n")

if __name__ == '__main__':
    directory = '.'
    read_files(directory)
