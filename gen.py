import yaml
import re

environment, functions = {}, {}

def process(page):
    temp_start = '<python>'
    temp_end = '</python>'
    regex = f"{temp_start}.+?{temp_end}"
    search_result = re.findall(regex, page, re.DOTALL)
    count = len(search_result)
    def get_replace(raw):
        last = raw.pop(-1)
        fname = f'python_script_{count-len(raw)}'
        code = f"def {fname}():\n" + last[len(temp_start):-len(temp_end)]
        print(fname)
        exec(code, environment, functions)
        results = ''.join(map(str, functions[fname]()))
        print(list(environment.keys()), list(functions.keys()))
        return results

    while True:
        if search_result != []:
            page = re.sub(regex, get_replace(search_result), page, 1, flags=re.DOTALL)
        else:
            break
    return page

# html = open("input.html").read()
res = process('''
<python>
    global i
    i = 1
    yield i
</python>
<python>
    yield i
</python>
''')

print(res)
with open("output.html", "w", encoding="utf-8") as output_file:
    pass
    # output_file.write(html)