from DumpParser import Parser
import os
from tqdm import tqdm
import re
import time
import utils

paths = {}

def convert_to_hook(offset_string, offset, class_name, file):
    function_name = offset_string.split("(")[0].split(" ")[-1]
    function_name = function_name.replace(".", "_")
    return_type = offset_string.split("(")[0].split(" ")[-2]
    real_type = return_type
    params_string = offset_string.split("(")[1].split(")")[0]
    
    params = re.findall(r"(\w+)\s+(\w+)", params_string)
    
    global paths
    
    def get_type(type):
        inbuilt_types = ["void", "bool", "byte", "char", "decimal", "double", "float", "int", "long", "sbyte", "short", "uint", "ulong", "ushort"]
        global paths
        if type in paths:
            return type + " *"
        elif type in inbuilt_types:
            return type
        else:
            return "void *"
    
    return_type = get_type(return_type)
    
    func_params = ", ".join([(f"{get_type(param_type)} {name}") for param_type, name in params])
    func_params_types = ", ".join([(f"{get_type(param_type)}") for param_type, name in params])
    
    call_params = ", ".join([f"{name}" for param_type, name in params])
    
    im = findImport(offset_string)
    
    if class_name == real_type:
        return_type = class_name + " *"
    elif im == "null":
        return_type = return_type
    else:
        return_type = real_type + " *"
        
    if return_type != "void":
        hook = f"{return_type} {function_name}({func_params}){{\n"
        hook += f"     \t\t{return_type} (*_{function_name})(void* thiz, {func_params_types}) = "
        hook += f"({return_type} (*)(void*, {func_params_types}))getAddress(\"libil2cpp.so\", {offset});\n"
        hook += f"    \t\treturn _{function_name}(this{', ' + call_params if call_params else ''});\n"
        hook += "\t\t}"
    else:
        hook = f"{return_type} {function_name}({func_params}){{\n"
        hook += f"     \t\t{return_type} (*_{function_name})(void* thiz, {func_params_types}) = "
        hook += f"({return_type} (*)(void*, {func_params_types}))getAddress(\"libil2cpp.so\", {offset});\n"
        hook += f"    \t\t_{function_name}(this{', ' + call_params if call_params else ''});\n"
        hook += "\t\t}"
    hook = ("//TYPE: "+real_type+"\n\t\t"+hook).replace(", )", ")")
    return hook

def hook_field_offset(data):
    global paths
    inbuilt_types = ["void", "bool", "byte", "char", "decimal", "double", "float", "int", "long", "sbyte", "short", "uint", "ulong", "ushort"]
    def get_type(type):
        inbuilt_types = ["void", "bool", "byte", "char", "decimal", "double", "float", "int", "long", "sbyte", "short", "uint", "ulong", "ushort"]
        global paths
        if type in paths:
            return type
        elif type in inbuilt_types:
            return type
        else:
            return "void"
    type_normal = get_type(data["type"])
    type = type_normal
    
    if type_normal in inbuilt_types:
        type = type_normal + " *"
        
    if type_normal == "void":   
        type = "void *"
    
    name = data["name"]
    offset = data["offset"]
    
    try:
        hook = f"{type} get_field_{name}() {{\n"
        hook += f"  \t\t\treturn *({type} *)(uintptr_t)(this + {offset});\n"
        hook += "   \t\t}\n"
        hook += f"  \t\tvoid set_field_{name}({type} data) {{\n"
        hook += f"   \t\t\t*({type} *)(uintptr_t)(this + {offset}) = data; \n \t\t}} \n"
        return hook
    except: 
        time.sleep(1)
        return data
    
def findImport(offset_string):
    global paths
    return_type = offset_string.split("(")[0].split(" ")[-2]
    if return_type in paths:
        return return_type
    else:
        return "null"
        
def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def sanitize_filename(filename):
    invalid_chars = {':', '*', '?', '<', '>', '|', '"', '/'}
    replace_chars = {'\\': '-', '/': '-', ':': '-', '*': '-', '?': '-', '<': '_', '>': '_', '|': '_', '"': '_'}
    
    for char in invalid_chars:
        filename = filename.replace(char, '')
        
    for char, replacement in replace_chars.items():
        filename = filename.replace(char, replacement)
    
    return filename

def write_class_methods(namespace):
    global paths
    base_directory = "."
    try:
        directory = os.path.join(base_directory, "parsed", sanitize_filename(namespace.name))
        create_directory(directory)
    except:
        pass
        
    for class_name, class_obj in tqdm(namespace.classes.items()):
        file_name = f"{class_name}.h"
        file_name = sanitize_filename(file_name)
        file_path = os.path.join(directory, file_name)
        classImports = {}
        classImports["utils_by_nepmods"] = "../utils.h"
        with open(file_path, "w") as file:
            for method_name, method_obj in class_obj.methods.items():
                method_template = method_obj.getMethodTemplate()
                im = findImport(method_template)
                if im != "null":
                    classImports[im] = paths[im]
                for i in method_obj.getAll()["params"]: 
                    try:
                        type = i.split(" ")[0]
                        if type in paths:
                            classImports[type] = paths[type]
                    except:
                        pass
                    
            for field_name, field_obj in class_obj.fields.items():
                type = field_obj.getAll()["type"]
                if type in paths:
                    classImports[type] = paths[type]
                    
            for import_name, import_path in classImports.items():
                file.write(f'#include "{import_path}"\n')
                
            file.write(f"\nclass {class_name} {{\n")
            file.write("\tpublic:\n")
            
            for field_name, field_obj in class_obj.fields.items():
                method_template = field_obj.getAll()
                hook = hook_field_offset(method_template)
                file.write(f"\t\t{hook}\n")
                
            for method_name, method_obj in class_obj.methods.items():
                method_template = method_obj.getMethodTemplate()
                offset = method_obj.getOffset()
                hook = convert_to_hook(method_template, offset, class_name, file)
                file.write(f"\t\t{hook}\n")
            
            file.write("};")
            
    for struct_name, struct_obj in tqdm(namespace.structs.items()):
        file_name = f"struct_{struct_name}.h"
        file_name = sanitize_filename(file_name)
        file_path = os.path.join(directory, file_name)
        classImports = {}
        classImports["utils_by_nepmods"] = "../utils.h"
        with open(file_path, "w") as file:
            for method_name, method_obj in struct_obj.methods.items():
                method_template = method_obj.getMethodTemplate()
                im = findImport(method_template)
                if im != "null":
                    classImports[im] = paths[im]
                for i in method_obj.getAll()["params"]: 
                    try:
                        type = i.split(" ")[0]
                        if type in paths:
                            classImports[type] = paths[type]
                    except:
                        pass
                    
            for field_name, field_obj in struct_obj.fields.items():
                type = field_obj.getAll()["type"]
                if type in paths:
                    classImports[type] = paths[type]
                    
            for import_name, import_path in classImports.items():
                file.write(f'#include "{import_path}"\n')
                
            file.write(f"\nstruct {struct_name} {{\n")
            file.write("\tpublic:\n")
            
            for field_name, field_obj in struct_obj.fields.items():
                method_template = field_obj.getAll()
                hook = hook_field_offset(method_template)
                file.write(f"\t\t{hook}\n")
                
            for method_name, method_obj in struct_obj.methods.items():
                method_template = method_obj.getMethodTemplate()
                offset = method_obj.getOffset()
                hook = convert_to_hook(method_template, offset, struct_name, file)
                file.write(f"\t\t{hook}\n")
            
            file.write("};")
            
def hasPath(lists, path):
    if path in lists:
        path = path + "_1"
        return hasPath(lists, path)
    else:
        return path
        
def set_import_path(namespace):
    global paths
    base_directory = "../"
    for class_name, class_obj in tqdm(namespace.classes.items()):
        key = hasPath(paths, class_name)
        path_name = os.path.join(base_directory, sanitize_filename(namespace.name), sanitize_filename(class_name)+".h")
        open("parsed/path.txt", "a").write(key + ": " + path_name + "\n")
        open("parsed/main.cpp", "a").write(f'#include "{path_name}"\n')
        paths[key] = path_name
    for struct_name, struct_obj in tqdm(namespace.structs.items()):
        key = hasPath(paths, "struct_"+struct_name)
        path_name = os.path.join(base_directory, sanitize_filename(namespace.name), sanitize_filename("struct_"+struct_name)+".h")
        open("parsed/path.txt", "a").write(key + ": " + path_name + "\n")
        open("parsed/main.cpp", "a").write(f'#include "{path_name}"\n')
        paths[key] = path_name
        
def main():
    dump_file_path = input("Enter Dump.cs Path: ")
    parser = Parser(dump_file_path)
    parser.init()
    
    base_directory = "."
    try:
        directory = os.path.join(base_directory, "parsed")
        create_directory(directory)
    except:
        pass
    open("parsed/path.txt", "w").write("")
    open("parsed/main.cpp", "w").write("")
    open("parsed/utils.h", "w").write(utils.getUtils())
    for namespace_name, namespace_obj in parser.namespaces.items():
        set_import_path(namespace_obj)
        
    for namespace_name, namespace_obj in parser.namespaces.items():
        write_class_methods(namespace_obj)
    
if __name__ == "__main__":
    main()