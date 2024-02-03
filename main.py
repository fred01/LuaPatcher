import logging
import os
import shutil

from luaparser import ast

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Specify your source and target directories here
source_directory = "/home/fred/tmp/Stars in Shadow/Lua state"
target_directory = "/home/fred/tmp/LuaState/"

# source_directory = "/home/fred/tmp/Mods/Source"
# target_directory = "/home/fred/tmp/Mods/Target"

# Create the target directory if it does not exist
os.makedirs(target_directory, exist_ok=True)


def clean_directory(target_directory):
    for filename in os.listdir(target_directory):
        file_path = os.path.join(target_directory, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')


clean_directory(target_directory)

total_files = 0
total_errors = 0
total_fixed = 0

for dirpath, dirnames, filenames in os.walk(source_directory):
    for filename in filenames:
        if filename.endswith('.lua'):
            total_files += 1
            source_filepath = os.path.join(dirpath, filename)

            # Create the equivalent path in the target directory
            target_dirpath = dirpath.replace(source_directory, target_directory)
            os.makedirs(target_dirpath, exist_ok=True)
            target_filepath = os.path.join(target_dirpath, filename)

            # Open each .lua file and read its content
            logging.info('Processing %s', source_filepath)
            logging.info('Writing to %s', target_filepath)
            with open(source_filepath, 'r', encoding='ISO-8859-1') as f:
                lines = f.read()

            try:
                tree = ast.parse(lines)
                fixed_lines = ast.to_lua_source(tree)
                with open(target_filepath, 'w') as f:
                    f.write(fixed_lines)
                total_fixed += 1
            except:
                total_errors += 1
                logging.info('Error parsing file', source_filepath)
                continue

logging.info('Total files: %d', total_files)
logging.info('Total errors: %d', total_errors)
logging.info('Total fixed: %d', total_fixed)
logging.info('Percent fixed: %d', total_fixed / total_files * 100)