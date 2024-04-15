import os
import re
import pickle
from collections import namedtuple

from .py_class import PyClass
from .utils import split_stub

P = namedtuple("Property", ["name", "type_str"])

def get_class_names(content:str):
    class_name = content[content.find("class ") + 6: content.find("(")]
    parent_name = content[content.find("(")+1: content.find(")")]
    # print(f"{class_name} {parent_name}")
    return class_name, parent_name

def get_docs(lines):
    start = -1
    end = -1
    for i, line in enumerate(lines):
        line = line.strip()
        if start != -1 and line.startswith('"""'):
            end = i
            break
        if start == -1 and line.startswith('r"""'):
            start = i
    return lines[start+1:end]


def get_editor_properties(lines):
    doc_lines = get_docs(lines)
    result = []
    for line in doc_lines:
        line = line.strip()
        if line.startswith('- ``'):
            property_name = line[4: line.find('``', 5)]
            property_type = line[line.find('(')+1: line.find(')')]
            # print(f"property name: {property_name}  type: {property_type}")
            result.append( P(name=property_name, type_str=property_type))
    return result


def get_functions(lines, b_debug=False):
    def get_name(line):
        assert "def" in line, f"line: {line}"
        return line[line.find("def ") + 4: line.find('(')]

    class_methods = []
    staticmethod = []
    methods = []
    property = []

    parts = []

    current = []

    doc_finished = False
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('"""') and not doc_finished:
            doc_finished = True
            continue
        if line.startswith("def") or line.startswith("@") and not doc_finished:
            doc_finished = True

        if not doc_finished:
            continue

        last_line = lines[i-1].strip() if i > 0 else ""
        if (line.startswith("@") and not line.startswith("@param ") and not line.startswith("@return ")) or (line.startswith("def ") and not last_line.startswith("@")):
            if current:
                parts.append(current)
                current = []

        current.append(line)
    # print("\n")
    

    for parts in parts:
        # print (f"\t{parts}")
        # print("~~")
        if parts[0].startswith("@"):
            n = get_name(parts[1])
            if (".setter") in parts[0] or "@property" in parts[0]:
                if n not in property:
                    property.append(n)
            elif "@staticmethod" in parts[0]:
                staticmethod.append(n)
            elif "@classmethod" in parts[0]:
                class_methods.append(n)
            else:
                print(f"unknown: {parts[0]}")
        else:
            methods.append(get_name(parts[0]))

    return class_methods, staticmethod, methods, property

def get_contents_in_blankets(lines):
    result = []
    line = ""
    for l in lines:
        line += l
    blanket_count = 0

    word = ""
    for c in line:
        if c == "(":
            blanket_count += 1
            word = ""
        elif c == ")":
            blanket_count -= 1
            if word:
                result.append(word)
                # assert len(word) < 50, word
            word = ""

        if blanket_count == 1 and c != "(":
            word += c
    return result

def get_relative(lines, keywords, class_name):
    content_in_blankets = get_contents_in_blankets(lines)
    result = dict()
    for word in content_in_blankets:
        if word in keywords and word != class_name:
            if word not in result:
                result[word] = 0
            result[word] += 1
    return result

def parse_unreal_class_stub(stub_lines: list, class_names: set):
    
    lines = stub_lines
    # assert lines[0].startswith("class")
    class_name, parent_name = get_class_names(lines[0])

    b_debug = False
    if class_name == "AutomationScheduler": # ue 4.27 AnimationScheduler is special, skip it
        print("skip AutomationScheduler")
        return None

    pyclass = PyClass(class_name)
    pyclass.parent = parent_name
    pyclass.editor_properties = get_editor_properties(lines)
    class_methods, staticmethod, methods, properties = get_functions(lines, b_debug=b_debug)
    pyclass.class_methods = class_methods
    pyclass.static_methods = staticmethod
    pyclass.methods = methods
    pyclass.properties = properties
    pyclass.references = get_relative(lines, class_names, pyclass.name)
    # print(f"references: {pyclass.references}")
    return pyclass


def parse_unreal_class_file(file_path, class_names):
    file_name = os.path.basename(file_path)
    if file_name.startswith("_"):
        return

    with open(file_path, 'r', encoding="UTF-8") as f:
        lines = f.readlines()
        # assert lines[0].startswith("class")
        class_name, parent_name = get_class_names(lines[0])

        pyclass = PyClass(class_name)
        pyclass.parent = parent_name
        pyclass.editor_properties = get_editor_properties(lines)
        class_methods, staticmethod, methods, properties = get_functions(lines)
        pyclass.class_methods = class_methods
        pyclass.static_methods = staticmethod
        pyclass.methods = methods
        pyclass.properties = properties
        pyclass.references = get_relative(lines, class_names, pyclass.name)
        # print(f"references: {pyclass.references}")
        return pyclass


def gen_relations(class_stubs:dict) -> dict:
    all_class = dict()
    all_class_names = class_stubs.keys()

    for class_name, class_stub in class_stubs.items():
        if class_name == "_Global":
            continue
        if class_name not in all_class:
            cls_ = parse_unreal_class_stub(class_stub, set(all_class_names))
            if cls_:
                all_class[class_name] = cls_
            else:
                print(f"Parse class: {class_name} failed")
        else:
            print(f"Class: {class_name} already exists")
    # get parent infos
    for name, c in all_class.items():
        parent_name = c.parent
        while parent_name in all_class:
            c.parents.insert(0, parent_name)
            parent = all_class[parent_name]
            parent_name = parent.parent
            c.generation += 1
        c.parents.insert(0, parent_name)
        c.grand_parent = parent_name

    for name, c in all_class.items():
        if c.parent:
            if c.parent in all_class:
                all_class[c.parent].children.append(c.name)
            else:
                print(f"\tCan't find parent name: {c.parent} in {c.name}")
        if c.references:
            for r_name, count in c.references.items():
                if r_name in all_class:
                    all_class[r_name].referenced_by[c.name] = count

    print(f"relationship generated: {len(all_class)} classes")
    return all_class
        




