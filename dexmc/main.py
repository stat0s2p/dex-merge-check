import argparse
import os
import sys
from logging import getLogger, INFO, error, info

from dexmc.objects import DexBuilderHome, ClassCounter


def main() -> int:
    parser = argparse.ArgumentParser('check dex merge conflict.')
    parser.add_argument('dir', help='conflict module directory path.')
    parser.add_argument('--verbose', help='show conflict class.')
    args = parser.parse_args()
    dex_builder_dir = os.path.join(args.dir, 'build', 'intermediates', 'transforms', 'dexBuilder')
    dex_builder_homes = DexBuilderHome.get_homes(dex_builder_dir)
    for home in dex_builder_homes:
        info(f'scanning build target:{home.name}')
        conflict_archives = set()
        home.scan_classes()
        for counter in home.class_counters.values():  # type:ClassCounter
            if counter.has_conflict():
                for archive in counter.archives:
                    conflict_archives.add(archive.archive_name())
                if args.verbose is not None:
                    error(f'[{home.name}]class path:{counter.class_name} has conflicts in:{counter.archives}.')
        if conflict_archives is not None:
            error(f'[{home.name}] has conflicts {len(conflict_archives)} libraries:{conflict_archives}.')
        else:
            info(f'[{home.name}] has no conflicts.')
        info(f'scanned build target:{home.name}')
    return 0


if __name__ == '__main__':
    getLogger().setLevel(INFO)
    code = main()
    sys.exit(code)
