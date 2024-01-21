import logging
import re
import os
import shutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Specify your source and target directories here
source_directory = "/home/fred/tmp/Stars in Shadow/Lua state"
target_directory = "/home/fred/tmp/LuaState/"

# Create the target directory if it does not exist
os.makedirs(target_directory, exist_ok=True)

# Regular expression pattern to find if statements without then
# elseif w.is_heavy
patterns = {
    r'(?<=\bif\b)(?!.*then).*': lambda line, match: line[:match.end()] + ' then' + line[match.end():],
    r'(?<=\belseif\b)(?!.*then).*': lambda line, match: line[:match.end()] + ' then' + line[match.end():],
    r'(?<=\bfor\b).*in(?!.*do).*': lambda line, match: line[:match.end()] + ' do' + line[match.end():],
    r'(?<=\bfor\b).*;(?!.*do).*': lambda line, match: line[:match.end()].replace(';', ' in') + ' do' + line[match.end():],
    r'([\w\[\]]+)\s*\+=\s*([\w\[\]]+)': lambda line, match: f'{match.group(1)} = {match.group(1)} + {match.group(2)}' + line[match.end():],
    # Add more patterns and functions as needed
}

# Clean the target directory
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


def fix_line(line):
    corrected_line = line
    for pattern, func in patterns.items():
        match = re.search(pattern, line)
        if match:
            corrected_line = func(line, match)
    return corrected_line


for dirpath, dirnames, filenames in os.walk(source_directory):
    for filename in filenames:
        if filename.endswith('.lua'):
            source_filepath = os.path.join(dirpath, filename)

            # Create the equivalent path in the target directory
            target_dirpath = dirpath.replace(source_directory, target_directory)
            os.makedirs(target_dirpath, exist_ok=True)
            target_filepath = os.path.join(target_dirpath, filename)

            # Open each .lua file and read its content
            logging.info('Processing %s', source_filepath)
            logging.info('Writing to %s', target_filepath)
            with open(source_filepath, 'r', encoding='ISO-8859-1') as f:
                lines = f.readlines()

            # Go through each line and find if statements without then
            with open(target_filepath, 'w') as f:
                for line in lines:
                    fixed_line = fix_line(line)
                    f.write(fixed_line)


# in_regex = r'(local\s+)?(\w+(\s*,\s*\w+)*)\s+in\s+([\w!?]+)'
# double_dot_in_function_regex = r'\w+\(.*\.\.\w+.*\)'


# # function to load source code from a file
# def load_source(filename):
#     with open(filename, 'r') as f:
#         return f.read()
#
#
# # function to write source code to a file
# def write_source(filename, source):
#     with open(filename, 'w') as f:
#         f.write(source)
#
#
# def transform_in(s):
#     matches = re.finditer(r'(local\s+)?(\w+(\s*,\s*\w+)*)\s+in\s+([\w!]+)', s, re.MULTILINE)
#     result = []
#     for match in matches:
#         local_keyword, vars, obj = match.group(1), match.group(2).split(','), match.group(4)
#         local_keyword = local_keyword if local_keyword else ''
#         result.append(local_keyword + ','.join(vars) + '=' + ','.join(f'{obj}.{var.strip()}' for var in vars))
#     return '\n'.join(result)
#
#
# def transform_insert(s):
#     pattern = r'\.\.(\w+)'
#     matches = re.finditer(pattern, s)
#     for match in matches:
#         var = match.group(1)
#         s = re.sub(r'\.\.' + var, f"'{var}', {var}", s)
#     return s
