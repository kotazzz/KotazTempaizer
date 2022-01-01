import glob
import os
import re
import sys
import traceback
from datetime import datetime
from inspect import currentframe, getframeinfo
import types
import yaml
from git import Repo

class TemplateProcessor:
    def __init__(self, open_tag = '<python>', close_tag = '</python>'):
        self.start = open_tag
        self.end = close_tag
        self.regex = f"{open_tag}.+?{close_tag}"
        self.global_counter = 0

    def process_tag(self, func_body, auto_str = True, insert = {}):
            self.global_counter += 1
            function_name = f"pytag_{self.global_counter}"
            code = f"def {function_name}():\n" + func_body
            compiled = compile(code, function_name, "exec")
            exec(compiled, dict(insert, **globals()), locals())
            try:
                if auto_str:
                    results = "".join(map(str, locals()[function_name]()))
                else:
                    results = list(locals()[function_name]())
            except Exception as e:
                tb = traceback.extract_tb(sys.exc_info()[2])
                tb_lines = [
                                '"{filename}" ({lineno}): {content}\n  > {line}\n'.format(
                                    filename=t.filename,
                                    lineno=t.lineno,
                                    content=t.name,
                                    line=t.line,
                                )
                                for t in tb
                            ]
                code_lines = code.split(chr(10))
                formated = (
                    "\n".join(
                        "".join(tb_lines).split("\n")[:-2]
                    )
                    + f"\n  > {code_lines[list(tb)[-1].lineno-1]}"
                    + f"\n{type(e).__name__}:  {e}"
                )
                sep = "\n" + "-" * 30 + "\n"
                print(code +'\n'+ formated+sep)

                return "<pre><code>" + formated + "</pre></code>"

            else:
                return results

    def process(self, text, insert = {}):
        search_result = re.findall(self.regex, text, re.DOTALL)
        search_result = search_result[::-1]
        max_count = len(search_result)
        self.global_counter = 0

        process_tag = self.process_tag
    
        while True:
            if search_result != []:
                last_res = search_result.pop(-1)
                raw_code = last_res[len(self.start) : -len(self.end)]
                text = re.sub(self.regex, process_tag(raw_code, insert=insert), text, 1, flags=re.DOTALL)
            else:
                break

        return text
class Loader:
    def get_paths(self, *path_patterns):
        result = []
        for pattern in path_patterns:
            result += glob.glob(os.getcwd() + pattern)
        return result

    def load_data(self, paths):
        data = types.SimpleNamespace()
        for path in paths:
            raw = open(path).read()
            value = yaml.safe_load(raw)
            filename = os.path.basename(path)
            ext = '.yml'
            setattr(data, filename[:-len(ext)], value)
        return data


    def load_plugins(self, paths):
        plugins = types.SimpleNamespace()
        tproc = TemplateProcessor()
        for path in paths:
            content = open(path).read()

            plugin_functions = tproc.process_tag(content, auto_str=False)
            plugin_namespace = types.SimpleNamespace()
            for func in plugin_functions:
                setattr(plugin_namespace, func.__name__, func)

            filename = os.path.basename(path)
            ext= '.html'
            setattr(plugins, filename[:-len(ext)], plugin_namespace)
        return plugins

    def load_templates(self, paths, env = {}):
        templates = types.SimpleNamespace()
        tproc = TemplateProcessor()
        for path in paths:
            content = open(path).read()
            filename = os.path.basename(path)
            ext = '.html'
            setattr(templates, filename[:-len(ext)], tproc.process(content, insert=env))
        return templates

class VerInfo:
    def __init__(self):
        repo = Repo(search_parent_directories=True)
        commits = list(repo.iter_commits("master", max_count=10000))
        last, first = commits[0], commits[-1]
        week = datetime.fromtimestamp(last.authored_date).strftime("%W")
        day = datetime.fromtimestamp(last.authored_date).strftime("%j")
        ddays = datetime.fromtimestamp(
            last.authored_date - first.authored_date
        ).strftime("%d")
        commit_count = len(commits)
        custom = f"R{week}W{day}D{ddays}DD.{commit_count}CC"
        normal = f"1.{ddays}.{commit_count}b"

        self.week = week
        self.day = day
        self.ddays = ddays
        self.commit_count = commit_count
        self.form_ver = f"1.{ddays}.{commit_count}b"
        self.full_ver = f"R{week}W{day}D{ddays}DD.{commit_count}CC"
        self.version = f"{self.form_ver} ({self.full_ver})"

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"<Version {self.commit_count=} {self.week=} {self.day=} {self.ddays=} {self.form_ver=} {self.full_ver=}>"
class Environment(object):
    def __init__(self, data_path_pattern = ["/data/*.yml", "/data/**/*.yml"],
    plugin_path_pattern = ["/plugins/*.html", "/plugins/**/*.html"], 
    template_path_pattern = ["/templates/*.html", "/templates/**/*.html"]):
        loader = Loader()
        data_paths = loader.get_paths(*data_path_pattern)
        plugin_paths = loader.get_paths(*plugin_path_pattern)
        template_paths = loader.get_paths(*template_path_pattern)
        self.data = loader.load_data(data_paths)
        self.plugins = loader.load_plugins(plugin_paths)
        self.templates = loader.load_templates(template_paths, {'env':self})

        self.verinfo = VerInfo()
        self.form_ver = self.verinfo.form_ver
        self.full_ver = self.verinfo.full_ver
        self.version = self.verinfo.version


def compile_site(*paths):
    
    global env
    env = Environment()
    loader = Loader()
    files = loader.get_paths(*paths)
    tproc = TemplateProcessor()
    for filepath in files:
        content = open(filepath).read()
        result = tproc.process(content)

        export_file  = filepath.replace("/src/", "/")
        export_folder = os.path.dirname(export_file)
        if not os.path.exists(export_folder):
            try:
                os.makedirs(export_folder)
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
        with open(export_file, "w", encoding="utf-8") as f:
            f.write(result)
compile_site(
        "/src/*.html",
        "/src/**/*.html",
    )
# 1) Load and proc data
# 2) Load and proc plugins 
# 3) Load and proc templates (req data plugins)
# 4) Load and proc src (req data plugins templates)

