import yaml
import re
import glob
import os
from git import Repo
from datetime import datetime
import traceback
import sys
from inspect import currentframe, getframeinfo

class Environment(object):
    def __init__(self):
        
        class VerInfo:
            def __init__(self):
                repo = Repo(search_parent_directories=True)
                commits = list(repo.iter_commits("master", max_count=10000))
                last, first = commits[0], commits[-1]
                week= datetime.fromtimestamp(last.authored_date).strftime('%W')
                day = datetime.fromtimestamp(last.authored_date).strftime('%j')
                ddays = datetime.fromtimestamp(last.authored_date-first.authored_date).strftime('%d')
                commit_count = len(commits)
                custom = f'R{week}W{day}D{ddays}DD.{commit_count}CC'
                normal = f'1.{ddays}.{commit_count}b'
                
                self.week= week
                self.day= day
                self.ddays= ddays
                self.commit_count= commit_count
                self.form_ver = f'1.{ddays}.{commit_count}b'
                self.full_ver = f'R{week}W{day}D{ddays}DD.{commit_count}CC'
                self.version = f'{self.form_ver} ({self.full_ver})'
            def __str__(self):
                return self.__repr__()
            def __repr__(self):
                return f'<Version {self.commit_count=} {self.week=} {self.day=} {self.ddays=} {self.form_ver=} {self.full_ver=}>'
        self.verinfo = VerInfo()
        self.form_ver =self.verinfo.form_ver
        self.full_ver =self.verinfo.full_ver
        self.version = self.verinfo.version

env = Environment()
patterns = ["/data/*.yml", "/data/**/*.yml"]
for pattern in patterns:
    all_path = glob.glob(os.getcwd() + pattern)
    for path in all_path:
        raw = open(path).read()
        content = yaml.safe_load(raw)
        setattr(env, os.path.basename(path)[:-4], content)
        

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
        comp = compile(code, fname, 'exec')
        exec(comp, globals(), locals())
        
        try:
            results = "".join(map(str, locals()[fname]()))
        except Exception as e:
            print(fname, e)
            tb = traceback.extract_tb(sys.exc_info()[2])
            return '<pre><code>'+'\n'.join(
                ''.join(
                ['"{filename}" ({lineno}): {content}\n  > {line}\n'.format(
                    filename= t.filename,
                    lineno= t.lineno,
                    content= t.name,
                    line= t.line,
                ) for t in tb]
            ).split('\n')[:-2]
            )+f'\n  > {code.split(chr(10))[list(tb)[-1].lineno-1]}\n{type(e).__name__}:  {e}'+'</pre></code>'

            
        else:
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
