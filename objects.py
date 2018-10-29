from __future__ import annotations

import json
import os
import platform
import re
import shutil
import tempfile
from logging import error, debug, info

from enjarify.enjarify.main import *


class ClassCounter:
    def __init__(self, class_name: str):
        self.class_name = class_name
        self.archives = list()

    def push_class(self, archive: Archive):
        self.archives.append(archive)

    def has_conflict(self) -> bool:
        return len(self.archives) > 1


class DexBuilderHome:
    def __init__(self, name: str, home_dir: str):
        self.home_dir = home_dir
        self.name = name
        self.class_counters = dict()

    def __push_class(self, archive: Archive, class_name: str):
        class_counter = self.class_counters.get(class_name)
        if class_counter is None:
            class_counter = ClassCounter(class_name)
            self.class_counters[class_name] = class_counter
        class_counter.push_class(archive)

    def __presented_archives(self) -> [Archive]:
        model_file = os.path.join(self.home_dir, '__content__.json')
        with open(model_file) as file_ref:
            content_json = json.load(file_ref)
        archives = list()
        for model in content_json:
            if model['present']:
                archive = Archive(self.home_dir, model)
                archives.append(archive)
        return archives

    def scan_classes(self):
        for archive in self.__presented_archives():
            def visitor(class_name: str):
                self.__push_class(archive, class_name)

            archive.scan_classes(visitor)

    @staticmethod
    def get_homes(dex_builder: str) -> [DexBuilderHome]:
        rs = list()
        for root, _, files in os.walk(dex_builder):
            if '__content__.json' in files:
                name = root.replace(dex_builder, '')
                dex_home = DexBuilderHome(name, root)
                rs.append(dex_home)
        return rs


class Archive:

    def __init__(self, archive_home: str, model: dict):
        self.model = model
        self.archive_home = archive_home

    def __str__(self):
        return self.archive_name()

    def __repr__(self):
        return self.archive_name()

    def archive_name(self) -> str:
        name = self.model['name']  # type:str
        scope = self.model['scopes'][0]
        if scope == 'PROJECT':
            return "(BUILD TARGET)"
        elif scope == 'SUB_PROJECTS':
            # :mylibrary-1
            rs = re.search(r'(\S*)-\d+', name)
            return rs.group(1)
        elif scope == 'EXTERNAL_LIBRARIES':
            if name.startswith('android.local.jars:'):
                rs = re.search(r'android\.local\.jars:(\S*?):\S+', name)
                return rs.group(1)
        return name

    def archive_file(self) -> str:
        if not self.model['present']:
            return ''
        f = self.model['format']
        index = self.model["index"]
        if f == 'DIRECTORY':
            return os.path.join(self.archive_home, f'{index}')
        elif f == 'JAR':
            return os.path.join(self.archive_home, f'{index}.jar')
        else:
            raise Exception(f'bad format:{f}')

    def scan_classes(self, visitor):
        if not self.model['present']:
            return
        f = self.model['format']
        ftype = self.model['types'][0]
        if ftype != 'DEX_ARCHIVE':
            return
        info(f'scanning archive:{self.archive_name()},index:{self.model["index"]}')
        if f == 'JAR':
            dir_name = tempfile.mkdtemp()
            try:
                shutil.unpack_archive(self.archive_file(), dir_name, format='zip')
                dex_file = os.path.join(dir_name, os.listdir(dir_name)[0])
                jar_file = self.__process(dex_file)
                with zipfile.ZipFile(jar_file) as zip_ref:
                    for name in zip_ref.namelist():  # type:str
                        visitor(os.path.splitext(name)[0])
            finally:
                shutil.rmtree(dir_name, ignore_errors=True)
            pass
        elif f == 'DIRECTORY':
            archive_file = self.archive_file()
            for root, _, _ in os.walk(archive_file):
                if root.endswith('.dex'):
                    cp = root.replace(archive_file, '')
                    if any(platform.win32_ver()):
                        cp = cp.replace('\\', '/')
                    cp = cp.lstrip('/')
                    visitor(cp)

    @staticmethod
    def __process(dex: str) -> str:
        dexs = [read(dex)]
        outname = os.path.splitext(dex)[0] + '-enjarify.jar'
        with open(outname, mode='xb') as outfile:
            opts = options.NONE

            classes = collections.OrderedDict()
            errors = collections.OrderedDict()
            for data in dexs:
                translate(data, opts=opts, classes=classes, errors=errors)
            writeToJar(outfile, classes)
            for name, e in sorted(errors.items()):
                error(name + e)
            debug('{} classes translated successfully, {} classes had errors'.format(len(classes), len(errors)))
            return outname
