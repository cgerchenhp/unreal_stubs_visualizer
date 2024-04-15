import os
from collections import OrderedDict

def split_stub(unreal_stub_file_path: str) -> OrderedDict:
    unreal_classes_in_stub = OrderedDict()

    if not os.path.exists(unreal_stub_file_path):
        print(f"file: {unreal_stub_file_path} not exists.")
        return

    with open(unreal_stub_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        doc_ranges = []

        class_name = "_Global"
        last_line_number = 0
        for line_number, line in enumerate(lines):
            if line[0:6] == "class " and line[:-1]:
                last_class_name = class_name
                class_name = line[6: line.find('(') ]
                # print("{} Class Name: {}   line: {}".format(line_number, last_class_name, line.strip()))
                doc_ranges.append([last_line_number, line_number, last_class_name])
                last_line_number = line_number
        # add the last content
        doc_ranges.append([last_line_number, len(lines)-1, class_name])

        for start, end, class_name in doc_ranges:
            unreal_classes_in_stub[class_name] = lines[start:end]

    print(f"Total {len(unreal_classes_in_stub)} classes found in the stub file.")
    return unreal_classes_in_stub

