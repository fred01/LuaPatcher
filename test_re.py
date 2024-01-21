import re

# Your string
# line = 'for _,fleet in rpairs | empire.fleets'
line = "print('adding trigger for',d,i,ship.name,w.parent_type,..d)"

# Regular expression pattern to find for loops without do
# pattern = r'(for .*?)(?!\sdo\b)'

pattern = r'\w+\(.*\.\.\w+.*\)'


# Use re.sub() to add ' do' to the end of the for loop

match = re.search(pattern, line)
if match:
    print(line[:match.end()])
else:
    print("No match")

# src = """
#     local order = {
#       ..planet.empire,
#       ..steal,
#       ..destroyed,
#       ..planet,
#       ..instance,
#     }
#
# """
#
# src1 = """
#     local order = {
#       ..steal,
#       ..planet.empire,
#       destroyed = destroyed,
#       planet = planet,
#       instance = instance,
#     }
# """
#
#
# src2 = """
# for k,v ; t
#     print(k,v)
# end
# """
#
# src3 = """
#       print(..y, k,..v)
# """
#
# src4 = """
#       print(y, ..k, #(v))
# """
