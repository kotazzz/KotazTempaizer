import functools
import glob
import os
import re
import sys
import traceback
import types
import logging
import errno
from datetime import datetime
from inspect import currentframe, getframeinfo


import yaml
from git import Repo

from typing import Optional

logging.basicConfig(
    filename="main.log",
    format="%(asctime)s %(levelname)s: %(message)s",
    encoding="utf-8",
    level=logging.INFO,
    datefmt="%m/%d/%Y %I:%M:%S %p",
)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))



class TemplateProcessor():
    def __init__(
        self,
        open_tag: Optional[str] = "<python>",
        close_tag: Optional[str] = "</python>",
    ) -> None:
        logging.info('Создан новый процессор')
        """Процессор, обрабатывающий текст, содержащий "островки" кода, которые будут заменены на результат работы этого кода

        :param open_tag: Открывайющий код тег. Defaults to "<python>".
        :type open_tag: str
        :param close_tag: Закрывающий код тег. Defaults to "</python>".
        :type close_tag: str

        """
        self.start = open_tag
        self.end = close_tag
        self.regex = f"{open_tag}.+?{close_tag}"
        self.global_counter = 0
    def process_tag(
        self,
        func_body: str,
        auto_str: Optional[bool] = True,
        insert: Optional[dict] = {},
    ) -> str:
        """Выполняет код в exec, во время ошибок возвращает html тег с текстом ошибки, во время успешного выполнения - результат

        :param func_body:str: Тело функции, которая будет запущена
        :param auto_str:Optional[bool]: Преобразовывать ли набор результатов в одну строку (Default value = True)
        :param insert:Optional[dict]: Дополнительный объект, который будет в словаре globals, предаваемом в exec (Default value = {})


        """
        self.global_counter += 1
        function_name = f"pytag_{self.global_counter}"
        code = f"def {function_name}():\n" + func_body
        compiled = compile(code, function_name, "exec")
        exec(compiled, dict(insert, **globals()), locals())

        autostr_log = "Автоматическое преобразование" if auto_str else "Сырой вид"
        insert_log = ", дополнительный объект" if insert else ""
        logging.info(f'Вычисление тега {function_name}... ({autostr_log}{insert_log})')

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
                "\n".join("".join(tb_lines).split("\n")[:-2])
                + f"\n  > {code_lines[list(tb)[-1].lineno-1]}"
                + f"\n{type(e).__name__}:  {e}"
            )
            sep = "\n" + "-" * 30 + "\n"
            print(code + "\n" + formated + sep)

            return "<pre><code>" + formated + "</pre></code>"

        else:
            return results

    def process(self, text: str, insert: Optional[dict] = {}) -> str:
        """Обрабатывает текст текст, содержащий островки кода

        :param text:str: Исходный текст
        :param insert:Optional[dict]: Дополнительный объект, который будет в словаре globals, предаваемом в exec (Default value = {})

        """
        
        insert_log = "(Дополнительный объект)" if insert else ""
        logging.info(f'Обработка текста... {insert_log}')

        search_result = re.findall(self.regex, text, re.DOTALL)
        search_result = search_result[::-1]
        max_count = len(search_result)
        self.global_counter = 0

        process_tag = self.process_tag

        while True:
            if search_result != []:
                last_res = search_result.pop(-1)
                raw_code = last_res[len(self.start) : -len(self.end)]
                text = re.sub(
                    self.regex,
                    process_tag(raw_code, insert=insert),
                    text,
                    1,
                    flags=re.DOTALL,
                )
            else:
                break

        return text


class Loader():
    """ """

    def get_paths(self, *path_patterns: list[str]) -> list[str]:
        """Получить все пути к файлам по переданным паттернам

        :param *path_patterns:list[str]: Список паттернов путей

        """
        
        result = []
        for pattern in path_patterns:
            result += glob.glob(os.getcwd() + pattern)
        logging.info(f'Получение файлов/путей {path_patterns}: {len(result)} результатов')
        return result

    def load_data(self, paths: list[str]) -> types.SimpleNamespace:
        """Загрузить все данные из файлов по перечисленным путям

        :param paths:list[str]: пути файлов .yml, которые надо загрузить

        """
        logging.info(f'Загрузка данных из {len(paths)} источников')
        data = types.SimpleNamespace()
        for path in paths:
            raw = open(path).read()
            value = yaml.safe_load(raw)
            filename = os.path.basename(path)
            ext = ".yml"
            setattr(data, filename[: -len(ext)], value)
        return data

    def load_plugins(self, paths: list[str]) -> types.SimpleNamespace:
        """Загрузить все функции и плагины из файлов по перечисленным путям

        :param paths:list[str]: пути файлов .html, которые надо загрузить

        """
        logging.info(f'Загрузка плагинов из {len(paths)} источников')
        plugins = types.SimpleNamespace()
        tproc = TemplateProcessor()
        for path in paths:
            content = open(path).read()

            plugin_functions = tproc.process_tag(content, auto_str=False)
            plugin_namespace = types.SimpleNamespace()
            for func in plugin_functions:
                setattr(plugin_namespace, func.__name__, func)

            filename = os.path.basename(path)
            ext = ".html"
            setattr(plugins, filename[: -len(ext)], plugin_namespace)
        return plugins

    def load_templates(
        self, paths: list[str], env: Optional[dict] = {}
    ) -> types.SimpleNamespace:
        """Загрузить все шаблоны из файлов по перечисленным путям

        :param paths:list[str]: пути файлов .html, которые надо загрузить
        :param env:Optional[dict]: Дополнительные объекты для процессора шаблонов (Default value = {})

        """
        logging.info(f'Загрузка шаблонов из {len(paths)} источников')
        templates = types.SimpleNamespace()
        tproc = TemplateProcessor()
        for path in paths:
            content = open(path).read()
            filename = os.path.basename(path)
            ext = ".html"
            setattr(
                templates, filename[: -len(ext)], tproc.process(content, insert=env)
            )
        return templates


class VerInfo():
    """Содержит некоторую информацию о репозитории, в котором находится скрипт"""
    
    def __init__(self) -> None:
        logging.info(f'Сборка информации о версии...')
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
        logging.info(f'Сборка информации о версии... {self.version}')
    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"<Version {self.commit_count=} {self.week=} {self.day=} {self.ddays=} {self.form_ver=} {self.full_ver=}>"


class Environment(object, ):
    """Среда выполнения для шаблонного процессора, связывающий разные его части"""

    def __init__(
        self,
        data_path_pattern: list[str] = ["/data/*.yml", "/data/**/*.yml"],
        plugin_path_pattern: list[str] = ["/plugins/*.html", "/plugins/**/*.html"],
        template_path_pattern: list[str] = [
            "/templates/*.html",
            "/templates/**/*.html",
        ],
    ) -> None:
        logging.info(f'Environment: сборка путей...')
        loader = Loader()
        data_paths = loader.get_paths(*data_path_pattern)
        plugin_paths = loader.get_paths(*plugin_path_pattern)
        template_paths = loader.get_paths(*template_path_pattern)
        logging.info(f'Environment: загрузка данных...')
        self.data = loader.load_data(data_paths)
        self.plugins = loader.load_plugins(plugin_paths)
        self.templates = loader.load_templates(template_paths, {"env": self})
        
        self.verinfo = VerInfo()
        self.form_ver = self.verinfo.form_ver
        self.full_ver = self.verinfo.full_ver
        self.version = self.verinfo.version
        logging.info(f'Environment: успех!')

def compile_file(content, to_path, tproc):
    logging.info(f'Сборка {to_path}')
    """Обработать файл и сохранить в новом месте

    :param from_path: путь исходного файла
    :param to_path: путь файла для сохранения
    :param tproc: процессор

    """
    
    result = tproc.process(content)

    
    export_folder = os.path.dirname(to_path)
    if not os.path.exists(export_folder):
        try:
            os.makedirs(export_folder)
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
    with open(to_path, "w", encoding="utf-8") as f:
        f.write(result)


def compile_site(*paths) -> None:
    """Собрать сайт по исходникам, которые перечислены

    :param *paths: пути исходников

    """

    global env
    env = Environment()
    loader = Loader()
    files = loader.get_paths(*paths)
    tproc = TemplateProcessor()
    for from_path in files:
        to_path = from_path.replace("/src/", "/")
        content = open(from_path).read()
        compile_file(content, to_path, tproc)

compile_site(
    "/src/*.html",
    "/src/**/*.html",
)
# 1) Load and proc data
# 2) Load and proc plugins
# 3) Load and proc templates (req data plugins)
# 4) Load and proc src (req data plugins templates)
