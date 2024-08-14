"""Script to help with quickly creating new entries for blocks, items, etc."""

import re
import shutil
from pathlib import Path

mcfuncs: dict[str, Path] = {
    'init': Path('Record Every Statistic/data/record_stats/functions/init.mcfunction'),
    'uninstall': Path('Record Every Statistic/data/record_stats/functions/uninstall.mcfunction'),
}

# Read relevant files, store their individual lines
lines: dict[str, list[str]] = {func:[] for func in mcfuncs}

with open(mcfuncs['init'], 'r', encoding='utf-8') as f:
    lines['init'] = f.readlines()

with open(mcfuncs['uninstall'], 'r', encoding='utf-8') as f:
    lines['uninstall'] = f.readlines()

line_format: dict[str, str] = {
    'init': 'scoreboard objectives add {objective} {criteria}:minecraft.{object_name} "{display_name}"\n',
    'uninstall': 'scoreboard objectives remove {objective} \n',
}

# Store the category name based off the given comment and the prefix used in the next line's objective name
category_names: dict[str, dict[str, str]] = {}
for n, line in enumerate(lines['init']):
    if line.startswith('#'):
        prefix_matches = re.search(r"""\w+\.(?=[^.]*)""", lines['init'][n+1])
        if not prefix_matches:
            raise ValueError(f'Could not find a prefix in the first objective in init.mcfunction following {repr(line)}'+
                f'(Next line is: {repr(lines["init"][n+1])})')
        prefix = prefix_matches.group(0)

        criteria_matches = re.search(r"""(minecraft\..*?):""", lines['init'][n+1])
        # Custom criteria are ignored, but we still need it in the categories list
        if (not criteria_matches) and (prefix != 'cu.'):
            raise ValueError(f'Could not find a criteria type in the first objective in init.mcfunction following {repr(line)}'+
                f'(Next line is: {repr(lines["init"][n+1])})')
        criteria = criteria_matches.group(1) if criteria_matches else ''

        category_names[line] = {'prefix': prefix, 'criteria': criteria}

# Reversed, for convenience
prefix_names: dict[str, dict[str, str]] = {info['prefix']:{'name': name, 'criteria': info['criteria']} for name, info in category_names.items()}

category_contents: dict[str, dict[str, list[str]]] = {func: {} for func in mcfuncs}

# Get all lines between comments and store them into categories
for func in mcfuncs:
    for n, cat in enumerate(category_names):
        cat_index: int = lines[func].index(cat) + 1
        next_cat_index: int = -1 if (n + 1) == len(category_names) else lines[func].index(tuple(category_names.keys())[n + 1])
        category_contents[func][cat] = lines[func][cat_index:next_cat_index]

def reconstruct(func_name: str) -> str:
    """Reconstructs the given mcfunction file contents based off what we have stored.

    Sorts each section alphabetically, but the categories themselves are kept in the original order they appeared in the file."""
    return ''.join([cat + ''.join(sorted(category_contents[func_name][cat])) for cat in category_names])

def insert_new_objective(object_name: str, target_categories: str | list='', copy_cat: str='', test_run: bool=False) -> None:
    """object_name must be the internal name of an item/block/mob in Minecraft, in snake_case: e.g. "iron_ingot", "birch_door", "blaze"

    target_categories can either be a string formatted like "prefix1.prefix2.prefix3." or a list of category prefixes.

    Alternatively, you can use copy_cat to use the same categories as an existing object's objectives.
    If copy_cast is used, target_categories will be ignored.

    Use test_run=True to prevent actually modifying the contents."""
    if (not copy_cat) and (not target_categories):
        raise ValueError('Either copy_cat or target_categories must be specified.')

    if copy_cat:
        target_categories = find_objective_categories(copy_cat)
    else:
        if isinstance(target_categories, str):
            target_categories = [cat + '.' for cat in target_categories.split('.') if cat != '']
        elif isinstance(target_categories, list):
            # Make sure it has the ending dot for our checks
            target_categories = [cat + ('.' if not cat.endswith('.') else '') for cat in target_categories]
        else:
            raise ValueError('Argument "target_categories" must be a string in the format of "prefix1.prefix2.prefix3." or a list of category prefixes.')

    if 'cu.' in target_categories:
        raise ValueError('Custom category objectives are not supported with this method.')

    if any((cat not in prefix_names) for cat in target_categories):
        raise ValueError(f'{repr(cat)} isn\'t in the list of category prefixes.')

    for func in mcfuncs:
        for prefix in target_categories:
            objective_name: str = prefix + ''.join([word.title() if object_name.split('_').index(word) != 0 else word for word in object_name.split('_')])
            criteria: str = prefix_names[prefix]['criteria']
            if prefix == 'd.':
                display_name: str = 'Killed By ' + object_name.replace('_', ' ').title()
            else:
                display_name: str = object_name.replace('_', ' ').title() + ' ' + prefix_names[prefix]['name'].replace('#', '').strip()
            new_line: str = line_format[func].format(
                objective = objective_name,
                object_name = object_name,
                criteria = criteria,
                display_name = display_name
            )

            if new_line in category_contents[func][prefix_names[prefix]['name']]:
                print(f'!!! Line already exists in {func}.mcfunction under {prefix_names[prefix]['name'].strip()}: {repr(new_line)}')
                continue
            print(f'Appending to {func}.mcfunction under {prefix_names[prefix]['name'].strip()}: {repr(new_line)}')
            if not test_run:
                category_contents[func][prefix_names[prefix]['name']].append(new_line)

def find_objective_categories(object_name: str) -> list[str]:
    """Looks for any instance of objectives with the given object_name in all files & categories."""
    found_categories: list[str] = []
    for func in mcfuncs:
        for cat in category_contents[func]:
            for line in category_contents[func][cat]:
                if object_name in line: # TODO: Use regex, this can be inaccurate
                    print(f'Found in {func}.mcfunction under {repr(cat)}: {repr(line)}')
                    found_categories.append(category_names[cat]['prefix'])
    return found_categories

def write_out() -> None:
    for func, file_path in mcfuncs.items():
        if input(f'About to overwrite "{file_path}"\nContinue? (y/n) ').lower() != 'y':
            print(f'"{file_path}" has not been modified.')
            continue
        backup_path: Path = Path(str(file_path) + '.backup')
        print(f'Backing file up to "{backup_path}" ...')
        shutil.copy(file_path, backup_path)
        print(f'Writing...')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(reconstruct(func))
            print('Complete.')
