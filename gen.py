import yaml
import re
import glob
import os


class Object(object):
    pass


environment = Object()


def process(page):
    temp_start = "<python>"
    temp_end = "</python>"
    regex = f"{temp_start}.+?{temp_end}"
    search_result = re.findall(regex, page, re.DOTALL)[::-1]
    count = len(search_result)

    def get_replace(raw):
        last = raw.pop(-1)
        fname = f"python_script_{count-len(raw)}"
        code = f"def {fname}():\n" + last[len(temp_start) : -len(temp_end)]
        exec(code, globals(), locals())
        results = "".join(map(str, locals()[fname]()))
        return results

    while True:
        if search_result != []:
            page = re.sub(regex, get_replace(search_result), page, 1, flags=re.DOTALL)
        else:
            break
    return page


# html = open("input.html").read()

patterns = ["/src/*.html", "/src/**/*.html"]
for pattern in patterns:
    all_path = glob.glob(os.getcwd() + pattern)
    for path in all_path:
        content = open(path).read()
        result = process(content)
        respath = path.replace("/src", "")
        if not os.path.exists(os.path.dirname(respath)):
            try:
                os.makedirs(os.path.dirname(respath))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
        with open(respath, "w", encoding="utf-8") as f:
            f.write(result)
