import os

import unreal_code_relations

def main():
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PythonStub")

    stub_file = os.path.join(folder, "unreal.py")
    class_stubs = unreal_code_relations.split_stub(stub_file)

    all_classes = unreal_code_relations.gen_relations(class_stubs)
    assert "Object" in all_classes.keys(), "'Object' not in all_classes"

    # delete the cache file, once your update the unreal.py, as the cache file is generated based on the unreal.py
    unreal_code_relations.draw(all_classes, local_folder=os.path.dirname(__file__), delete_cache=True, iter_count=8)

if __name__ == "__main__":
    main()