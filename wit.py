from datetime import datetime
from distutils.dir_util import copy_tree

import filecmp
import itertools
import os

from os import listdir
from os import path

import random
import shutil
import sys

import matplotlib.pyplot as plt
import networkx as nx
import pylab


IMG_NAME_LENGTH = 40
FUNC_ARG = 1
FUNC_WITH_PARAM_ARGS = 2
LAST_MODIFIED_ATTR_STAT = 8


class WitNotFoundInSuperDirsError(Exception):
    pass


class CheckoutFailedError(Exception):
    pass


class NoSuchBranchNameError(Exception):
    pass


def get_file_contents(file_path):
    try:
        with open(file_path, 'r') as f:
            contents = f.read().strip()
    except (IsADirectoryError, PermissionError) as err:
        msg = f"Can't find file '{path}'.\t{err}."
        print(msg)
        return
    except TypeError as err:
        print(err)
        return
    except OSError:
        print(f"Access to the file {path} failed")
    else:
        return contents


def append_to_file_contents_in_path(path, contents, open_ver='a'):
    try:
        with open(path, open_ver) as f:
            f.write(contents)
    except (IsADirectoryError, PermissionError) as err:
        msg = f"Can't find file '{path}'.\t{err}."
        print(msg)
        return
    except TypeError as err:
        print(err)
        return
    except OSError:
        print(f"Creation of the file {path} or its edition failed")
    else:
        print(f"{path} - Creation\Edition finished Successfully.")


def creat_dir_in_path(path):
    try:
        os.mkdir(path)
    except OSError:
        print(f"Creation of the directory {path} failed")
    else:
        print(f"Successfully created the directory {path}")


def change_cwd_to_path(path):
    try:
        os.chdir(path)
    except OSError:
        print(f"Changing of the directory {path} failed")
    else:
        print(f"Successfully changed the current directory to {path}")


def get_file_lines(file_path):
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r') as f:
            contents = [line.strip() for line in f.readlines()]
    except (IsADirectoryError, PermissionError) as err:
        msg = f"Can't find file '{path}'.\t{err}."
        print(msg)
        return
    except TypeError as err:
        print(err)
        return
    except OSError:
        print(f"Access to the file {path} failed")
    else:
        return contents


def split_path_to_parts(path):
    folders = []
    end = True
    while end:
        path, folder = os.path.split(path)

        if folder != "":
            folders.append(folder)
        else:
            if path != "":
                folders.append(path)
            end = False
    folders.reverse()
    return folders


def get_head(file_path):
    contents = get_file_lines(file_path)
    head = contents[0].split('=')
    return head[1]


def get_parents(file_path):
    contents = get_file_lines(file_path)
    head = contents[0].split('=')
    return head[1].split(',')


def update_head_utility(file_path, commit_id):
    contents = get_file_lines(file_path)
    head = contents[0].split('=')
    head[1] = commit_id
    contents[0] = '='.join(head)
    return '\n'.join(contents)


def update_head(file_path, commit_id):
    if not os.path.exists(file_path):
        return None
    new_contents = update_head_utility(file_path, commit_id)
    try:
        with open(file_path, 'w') as f:
            f.write(new_contents)
    except (IsADirectoryError, PermissionError) as err:
        msg = f"Can't find file '{path}'.\t{err}."
        print(msg)
        return
    except TypeError as err:
        print(err)
        return
    except OSError:
        print(f"Access to the file {path} failed")


def is_master_and_head_different(ref_file):
    contents = get_file_lines(ref_file)
    head = contents[0].split('=')
    master = contents[1].split('=')
    return master == head


def get_commit_id_by_master(ref_file):
    contents = get_file_lines(ref_file)
    master = contents[1].split('=')
    return master[1]


def append_branch_name_to_references(file_path, name, commit_id):
    branch_section = '='.join([name, commit_id])
    append_to_file_contents_in_path(file_path, '\n'+ branch_section, 'a')


def join_path_parts(path_parts):
    merge = path_parts[0]
    for part in path_parts[1:]:
        merge = os.path.join(merge, part)
    return merge


def is_head_on_activated_branch(ref_file, activated_file, branch_name):
    try:
        branch_commit_id = get_commit_id_by_branch_name(ref_file, branch_name)
    except KeyError:
        return False
    else:
        head = get_head(ref_file)
        activated_branch = get_file_contents(activated_file)
        return head == branch_commit_id and activated_branch == branch_name


def walk_up(bottom, limit='.wit'):
    path_to_copy = []
    bottom = path.realpath(bottom)
    path_parts = split_path_to_parts(bottom)
    for i in reversed(range(len(path_parts))):
        curr_path = join_path_parts(path_parts[:i + 1])
        if path.exists(os.path.join(curr_path, limit)):
            return os.path.join(curr_path, limit), path_to_copy
        path_to_copy.insert(0, os.path.basename(curr_path))
    return


def copy_to_staging_area(path_parts, dest, rel_path):
    curr_dir = dest
    for dir_name in path_parts[:-1]:
        creat_dir_in_path(os.path.join(curr_dir, dir_name))
        curr_dir = os.path.join(curr_dir, dir_name)
    if os.path.isdir(rel_path):
        dir_name = os.path.basename(rel_path)
        creat_dir_in_path(os.path.join(curr_dir, dir_name))
        curr_dir = os.path.join(curr_dir, dir_name)
        copy_tree(rel_path, curr_dir)
    else:
        shutil.copy(rel_path, curr_dir)


def get_files_in_dir(path):
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            yield os.path.abspath(os.path.join(dirpath, f))


def get_rel_path_to_staging_area(path):
    return path.split('staging_area')[-1].lstrip('\\')


def get_rel_path_to_source_dir(source_dir_path, path):
    return path.split(source_dir_path)[-1].lstrip('\\')


def get_rel_path_to_commit_id(path, commit_id):
    return path.split(commit_id)[-1].lstrip('\\')


def get_changes_not_staged_for_commit(source_dir, staging_area):
    for dirpath, _, filenames in os.walk(staging_area):
        concat_to_rel_path = get_rel_path_to_staging_area(dirpath)
        for f in filenames:
            in_staging_area = os.path.join(staging_area, os.path.join(concat_to_rel_path, f))
            in_source_dir = os.path.join(source_dir, os.path.join(concat_to_rel_path, f))
            if not filecmp.cmp(in_source_dir, in_staging_area) or not filecmp.cmp(in_source_dir, in_staging_area, shallow=False):
                yield os.path.abspath(in_staging_area)


def change_source_dir_from_last_commit_id(source_dir, commit_id_path, commit_id):
    for dirpath, _, filenames in os.walk(commit_id_path):
        concat_to_rel_path = get_rel_path_to_commit_id(dirpath, commit_id)
        for f in filenames:
            in_commit_id = os.path.join(commit_id_path, os.path.join(concat_to_rel_path, f))
            in_source_dir = os.path.join(source_dir, os.path.join(concat_to_rel_path, f))
            if not os.path.isdir(in_commit_id):
                print(in_commit_id)
                print(in_source_dir)
                shutil.copy(in_commit_id, in_source_dir)


def get_commits_list(img_path):
    return [os.path.basename(f).rstrip('.txt') for f in listdir(img_path) if path.isfile(path.join(img_path, f))]


def get_commit_id_by_branch_name(ref_file, name):
    contents = get_file_lines(ref_file)
    commits_dictionary = dict([tuple(line.split('=')) for line in contents[2:]])
    return commits_dictionary[name]


def get_commits_section(ref_file):
    contents = get_file_lines(ref_file)
    return '\n'.join(contents[2:])


def get_commits_section_after_change_commit_of_branch(ref_file, name, new_commit):
    contents = get_file_lines(ref_file)
    commits_dictionary = dict([tuple(line.split('=')) for line in contents[2:]])
    commits_dictionary[name] = new_commit
    lines = []
    for t in list(commits_dictionary.items()):
        lines.append('='.join(t))
    return '\n'.join(lines)


def get_edges_list():
    wit_path = find_wit_dir()
    edges = []
    ref_file = os.path.join(wit_path, 'references.txt')
    child = get_head(ref_file)
    edges = edges + get_edges_list_util(child, edges, wit_path)
    return list(set(edges[:-1]))


def get_edges_list_util(child, edges, wit_path):
    if child:
        path_to_parent = os.path.join(wit_path, os.path.join('images', f'{child}.txt'))
        parents = get_parents(path_to_parent)
        for p in parents:
            if p != 'None':
                edges.append((child, p))
                edges += get_edges_list_util(p, edges, wit_path)
        return edges
    return []


def bfs(wit_path, root):
    commits = get_commits_list(os.path.join(wit_path, 'images'))
    values = [False] * len(commits)
    visited = dict(zip(commits, values))
    queue = []
    commits_by_levels = []
    queue.append(root)
    visited[root] = True
    while queue:
        root = queue.pop(0)
        commits_by_levels.append(root)
        path_to_adjacent_commits = os.path.join(wit_path, os.path.join('images', f'{root}.txt'))
        adjacent_commits = get_parents(path_to_adjacent_commits)
        for i in adjacent_commits:
            if i != 'None' and not visited[i]:
                queue.append(i)
                visited[i] = True
    return commits_by_levels


def find_wit_dir():
    wit_and_path_to_copy = walk_up(os.getcwd())
    if not wit_and_path_to_copy:
        raise WitNotFoundInSuperDirsError(f"Can't find '.wit' directory for path '{os.getcwd()}'")
    return wit_and_path_to_copy[0]


def init():
    wit = os.path.join(os.getcwd(), ".wit")
    creat_dir_in_path(wit)
    change_cwd_to_path(wit)
    images = os.path.join(os.getcwd(), "images")
    creat_dir_in_path(images)
    staging_area = os.path.join(os.getcwd(), "staging_area")
    creat_dir_in_path(staging_area)
    activated_file = os.path.join(wit, 'activated.txt')
    append_to_file_contents_in_path(activated_file, 'master', 'w')


def add(input_path):
    wit_and_path_to_copy = walk_up(input_path)
    if not wit_and_path_to_copy:
        raise WitNotFoundInSuperDirsError(f"Can't find '.wit' directory for path '{input_path}'")
    wit_path = wit_and_path_to_copy[0]
    path_to_copy = wit_and_path_to_copy[1]
    dest = os.path.join(wit_path, 'staging_area')
    copy_to_staging_area(path_to_copy, dest, input_path)


def commit(additional_parent=None, merge=False):
    wit_path = find_wit_dir()
    staging_area = os.path.join(wit_path, 'staging_area')
    moddate_staging_area = os.stat(staging_area)[LAST_MODIFIED_ATTR_STAT]
    moddate_last_commit = os.stat(os.path.join(wit_path, 'images'))[LAST_MODIFIED_ATTR_STAT]
    if moddate_staging_area <= moddate_last_commit:
        print("No Pending Changes.")
        return
    rand_name = ''.join(random.choices('1234567890abcdef', k=IMG_NAME_LENGTH))
    img = os.path.join(wit_path, os.path.join('images', rand_name))
    creat_dir_in_path(img)
    msg_file = os.path.join(wit_path, os.path.join('images', f'{rand_name}.txt'))
    now = datetime.now()
    date = now.strftime("%a %b %d %H:%M:%S %Y +0300")
    ref_file = os.path.join(wit_path, 'references.txt')
    parent = get_head(ref_file)
    if not additional_parent:
        contents = f'parent={parent}\ndate={date}\nmessage={sys.argv[FUNC_WITH_PARAM_ARGS]}'
    else:
        contents = f'parent={parent},{additional_parent}\ndate={date}\nmessage={sys.argv[FUNC_WITH_PARAM_ARGS]}'
    append_to_file_contents_in_path(msg_file, contents)
    copy_tree(staging_area, img)
    activated_file = os.path.join(wit_path, 'activated.txt')
    active_branch = get_file_contents(activated_file)
    # branch_in_ref = get_branch_name_and_its_commit_id(ref_file)
    if not merge and not is_master_and_head_different(ref_file) and active_branch == 'master':
        append_to_file_contents_in_path(ref_file, f'HEAD={rand_name}\nmaster={rand_name}\n{get_commits_section(ref_file)}', 'w')
    elif is_head_on_activated_branch(ref_file, activated_file) or merge:
        append_to_file_contents_in_path(ref_file, f'HEAD={rand_name}\nmaster={get_commit_id_by_master(ref_file)}\n{get_commits_section_after_change_commit_of_branch(ref_file, active_branch, rand_name)}', 'w')
    else:
        append_to_file_contents_in_path(ref_file,
                                        f'HEAD={rand_name}\nmaster={get_commit_id_by_master(ref_file)}\n{get_commits_section(ref_file)}',
                                        'w')


def get_status():
    wit_path = find_wit_dir()
    ref_file = os.path.join(wit_path, 'references.txt')
    head = get_head(ref_file)
    staging_area = os.path.join(wit_path, 'staging_area')
    changes_to_be_committed = []
    for file in get_files_in_dir(staging_area):
        changes_to_be_committed.append(file)
    changes_not_staged_for_commit = []
    source_dir = os.path.abspath(os.path.join(wit_path, '..'))
    for file in get_changes_not_staged_for_commit(source_dir, staging_area):
        changes_not_staged_for_commit.append(file)
    files_in_source_dir = [get_rel_path_to_source_dir(source_dir, path) for path in get_files_in_dir(source_dir) if os.path.join('.wit', '') not in path]
    files_in_staging_area = [get_rel_path_to_staging_area(path) for path in get_files_in_dir(staging_area)]
    untracked_files = []
    for file in files_in_source_dir:
        if file not in files_in_staging_area:
            untracked_files.append(file)
    return {'head': head, 'changes_to_be_committed': changes_to_be_committed, 'changes_not_staged_for_commit': changes_not_staged_for_commit, 'untracked_files': untracked_files}


def status():
    stat = get_status()
    print(f"Current commit id:\n{stat.get('head')}")
    print("\nChanges to be committed:")
    for file in stat.get('changes_to_be_committed'):
        print(file)
    print("\nChanges not staged for commit:")
    for file in stat.get('changes_not_staged_for_commit'):
        print(file)
    print("\nUntracked files:")
    for file in stat.get('untracked_files'):
        print(file)


def checkout(commit_id):
    wit_path = find_wit_dir()
    ref_file = os.path.join(wit_path, 'references.txt')
    stat = get_status()
    if len(stat.get('changes_to_be_committed')) or len(stat.get('changes_not_staged_for_commit')):
        raise CheckoutFailedError("Checkout Failed - files are not prepared for checkout.")
    if commit_id == 'master':
        commit_id = get_commit_id_by_master(ref_file)

    # if it branch name
    if commit_id not in get_commits_list():
        branch_name = commit_id
        commit_id = get_commit_id_by_branch_name(ref_file, branch_name)
        if not commit_id:
            raise NoSuchBranchNameError("No such branch name.")
        activated_file = os.path.join(wit_path, 'activated.txt')
        append_to_file_contents_in_path(activated_file, branch_name, 'w')

    update_head(ref_file, commit_id)
    source_dir = os.path.abspath(os.path.join(wit_path, '..'))
    commit_id_path = os.path.join(wit_path, os.path.join('images', commit_id))
    change_source_dir_from_last_commit_id(source_dir, commit_id_path, commit_id)


def graph():
    wit_path = find_wit_dir()
    ref_file = os.path.join(wit_path, 'references.txt')
    head = get_head(ref_file)
    G = nx.DiGraph()
    edges_list = get_edges_list()
    G.add_edge('Head', head, lable='Head', edge_size=0.001, edge_length=0.001)
    G.add_edges_from(edges_list, edge_size=0.01)
    edge_colors = ['black' for _ in G.edges()]
    node_colors = ['white'] + ['red' for i in range(1, len(G.nodes()))]
    pos = nx.spring_layout(G)
    nx.draw(G, pos, node_color=node_colors, node_size=1000, edge_color=edge_colors, edge_cmap=plt.cm.Reds, with_labels=True)
    pylab.show()


def branch(name):
    wit_path = find_wit_dir()
    ref_file = os.path.join(wit_path, 'references.txt')
    head = get_head(ref_file)
    append_branch_name_to_references(ref_file, name, head)


def merge_version_add(input_path, wit_path, commit_id):
    commit_and_path_to_copy = walk_up(input_path, commit_id)
    path_to_copy = commit_and_path_to_copy[1]
    dest = os.path.join(wit_path, 'staging_area')
    copy_to_staging_area(path_to_copy, dest, input_path)


def merge(name):
    wit_path = find_wit_dir()
    ref_file = os.path.join(wit_path, 'references.txt')
    name_commit_id = get_commit_id_by_branch_name(name)
    head = get_head(ref_file)
    head_commits_history = bfs(wit_path, head)
    branch_commits_history = bfs(wit_path, name_commit_id)
    common_commit = None
    i = 0
    to_staging_real_and_rel_paths = {}
    while not common_commit and i < len(branch_commits_history):
        commit_id_path = os.path.join(wit_path, os.path.join('images', branch_commits_history[i]))
        for f in get_files_in_dir(commit_id_path):
            relative = get_rel_path_to_commit_id(f, branch_commits_history[i])
            if relative not in to_staging_real_and_rel_paths.values():
                to_staging_real_and_rel_paths[(f, branch_commits_history[i])] = relative
        if branch_commits_history[i] in head_commits_history:
            common_commit = branch_commits_history[i]
        i += 1
    for path, commit_id in to_staging_real_and_rel_paths.keys():
        merge_version_add(path, wit_path, commit_id)
    commit(name_commit_id, True)


if sys.argv[FUNC_ARG] == 'init':
    init()
if sys.argv[FUNC_ARG] == 'status':
    status()
if sys.argv[FUNC_ARG] == 'add' and len(sys.argv) == FUNC_WITH_PARAM_ARGS + 1:
    add(sys.argv[FUNC_WITH_PARAM_ARGS])
if sys.argv[FUNC_ARG] == 'commit' and len(sys.argv) == FUNC_WITH_PARAM_ARGS + 1:
    commit()
if sys.argv[FUNC_ARG] == 'checkout' and len(sys.argv) == FUNC_WITH_PARAM_ARGS + 1:
    checkout(sys.argv[FUNC_WITH_PARAM_ARGS])
if sys.argv[FUNC_ARG] == 'graph':
    graph()
if sys.argv[FUNC_ARG] == 'branch' and len(sys.argv) == FUNC_WITH_PARAM_ARGS + 1:
    branch(sys.argv[FUNC_WITH_PARAM_ARGS])
if sys.argv[FUNC_ARG] == 'merge' and len(sys.argv) == FUNC_WITH_PARAM_ARGS + 1:
    merge(sys.argv[FUNC_WITH_PARAM_ARGS])