import os
import shutil

def copy_files(src_dir, dest_dir):
    for root, dirs, files in os.walk(src_dir):
        # Исключаем папку 'levels' из обхода
        if 'levels' in dirs:
            dirs.remove('levels')
        rel_path = os.path.relpath(root, src_dir)
        dest_subdir = os.path.join(dest_dir, rel_path)
        os.makedirs(dest_subdir, exist_ok=True)
        for file in files:
            src_file = os.path.join(root, file)
            dest_file = os.path.join(dest_subdir, file)
            try:
                shutil.copy2(src_file, dest_file)
                print(f"Скопирован: {src_file} -> {dest_file}")
            except PermissionError as e:
                print(f"Ошибка доступа при копировании {src_file}: {e}")
            except Exception as e:
                print(f"Ошибка при копировании {src_file}: {e}")

if __name__ == '__main__':
    source_directory = '.'
    destination_directory = './copy'
    copy_files(source_directory, destination_directory)
