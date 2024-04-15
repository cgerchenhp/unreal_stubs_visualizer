class PyClass(object):
    def __init__(self, name):
        self.name = name
        self.parent = None
        self.parents = []
        self.grand_parent = None
        self.generation = -1
        self.children = []

        self.editor_properties = []
        self.properties = []

        self.static_methods = []
        self.methods = []
        self.class_methods = []

        self.referenced_by = {}
        self.references = {}

    def get_referenced_by_pure(self):
        return len(set(self.referenced_by) - set(self.children)- set(self.parents))

    def get_references_pure(self):
        return len(set(self.references) - set(self.children)- set(self.parents))

    def get_type(self):
        temp = self.parents[:]
        temp.append(self.name)
        for p in temp:
            if p == "Object":
                return "Object"
            elif p == "EnumBase":
                return "Enum"
            elif p == "DelegateBase":
                return "Delegate"
            elif p == "StructBase":
                return "Struct"
            elif p == "MulticastDelegateBase":
                return "MultiDelegate"

        # print(f"unknow type: {self.name}'s parent: {self.parents}, grand: {self.grand_parent}")
        if not self.parents:
            print(f"\tEmpty parents: {self.name}")

        return self.grand_parent

    def __repr__(self):
        return (f"{self.name}({self.generation}), parent: {self.parent}, children: {len(self.children)}, "
                f"referenced_by: {len(self.referenced_by)}, references: {len(self.references)}, "
                f"property: {len(self.editor_properties)} {len(self.properties)}, "
                f"method: {len(self.static_methods)} {len(self.methods)} {len(self.class_methods)}")
