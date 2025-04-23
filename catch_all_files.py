import os

def collect_python_files_content(src_dir, output_file):
    # Открываем файл для записи результатов (режим 'w' автоматически очищает файл)
    with open(output_file, 'w', encoding='utf-8') as f:
        for root, dirs, files in os.walk(src_dir):
            # Исключаем папку 'levels' из обхода
            if 'levels' in dirs:
                dirs.remove('levels')
            
            rel_path = os.path.relpath(root, src_dir)
            
            for file in files:
                # Обрабатываем только Python файлы
                if not file.endswith('.py'):
                    continue
                    
                src_file = os.path.join(root, file)
                
                # Формируем путь к файлу относительно исходной директории
                if rel_path == '.':
                    file_path = file
                else:
                    file_path = os.path.join(rel_path, file)
                
                # Пропускаем сам выходной файл, чтобы избежать рекурсивного чтения
                if file == output_file:
                    continue
                    
                # Записываем информацию о файле в output_file
                f.write(f"#{file_path}\n")
                    
                try:
                    with open(src_file, 'r', encoding='utf-8') as source_file:
                        content = source_file.read()
                        f.write(content)
                        f.write('\n\n')
                except UnicodeDecodeError:
                    f.write(f"[Двоичный файл, содержимое не отображается]\n\n")
                except Exception as e:
                    f.write(f"[Ошибка при чтении файла: {e}]\n\n")
                    print(f"Ошибка при обработке файла {src_file}: {e}")

if __name__ == '__main__':
    source_directory = '.'
    output_file = 'to_gpt.txt'
    collect_python_files_content(source_directory, output_file)
    print(f"Содержимое Python файлов успешно сохранено в {output_file}")