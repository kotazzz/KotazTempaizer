import yaml
import re
class Object(object):
    pass

environment = Object()
environment.i = 1
def process(page):
    temp_start = '<python>'
    temp_end = '</python>'
    regex = f"{temp_start}.+?{temp_end}"
    search_result = re.findall(regex, page, re.DOTALL)[::-1]
    count = len(search_result)
    def get_replace(raw):
        last = raw.pop(-1)
        fname = f'python_script_{count-len(raw)}'
        code = f"def {fname}():\n" + last[len(temp_start):-len(temp_end)]
        exec(code, globals(), locals())
        results = ''.join(map(str, locals()[fname]()))
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
    yield 2
    environment.i = 1
    yield environment.i
</python>
<python>
    yield 1
</python>
''')
res2 = process('''
<python>
    yield environment.i
</python>
''')

print(res, res2)
with open("output.html", "w", encoding="utf-8") as output_file:
    pass
    # output_file.write(html)