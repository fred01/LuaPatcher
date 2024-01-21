from luaparser import ast

lines = """
local a = b!
"""

tree = ast.parse(lines)

# print(ast.to_pretty_str(tree))

print(ast.to_lua_source(tree))
