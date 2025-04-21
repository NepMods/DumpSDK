import json
import base64
import time
import os
from tqdm import tqdm
import sys
from json import JSONEncoder

class CustomEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Namespace):
            return self.serialize_namespace(obj)
        elif isinstance(obj, Method):
            return obj.name
        elif isinstance(obj, Enum):
            return obj.getAll()
        return super().default(obj)

    def serialize_namespace(self, namespace):
        data = {
            "name": namespace.name,
            "classes": {},
            "enums": {},
            "structs": {}
        }

        for key, value in namespace.classes.items():
            data["classes"][key] = value.getAll()

        for key, value in namespace.enums.items():
            data["enums"][key] = value.getAll()

        for key, value in namespace.structs.items():
            data["structs"][key] = value.getAll()

        return data

class Method:
    def __init__(self, data):
        self.name = data

    def getAll(self):
        ret = self.name
        ret["method"] = self.getMethodTemplate()
        return ret

    def getOffset(self):
        return self.name["offset"]

    def getMethodTemplate(self):
        mt = ""
        for i in self.name["modifier"]:
            mt += i + " "
        mt += self.name["type"] + " " + self.name["name"] + "("
        j = 0
        for i in self.name["params"]:
            if j == len(self.name["params"]) - 1:
                mt += i
            else:
                mt += i + ", "
            j += 1
        mt += ") { }"
        return mt

class Field:
    def __init__(self, data):
        self.name = data

    def getOffset(self):
        return self.name["offset"]

    def getAll(self):
        return self.name

class Class:
    def __init__(self, name):
        self.data = name
        self.fields = {}
        self.methods = {}
        self.name = name["name"]
        self.modifier = name["modifier"]

    def addField(self, key, data):
        self.fields[key] = Field(data)

    def addMethod(self, key, data):
        self.methods[key] = Method(data)

    def get(self, name):
        ret = {}
        i = 0
        for key in self.methods:
            if name == key:
                ret[i] = self.methods[key]
            i += 1
        for key in self.fields:
            if name == key:
                ret[i] = self.fields[key]
            i += 1
        return ret

    def getAll(self):
        ret = {}
        ret["fields"] = {}
        ret["name"] = self.name
        ret["modifier"] = self.modifier
        for key in self.fields:
            ret["fields"][key] = self.fields[key].getAll()

        ret["methods"] = {}
        for key in self.methods:
            ret["methods"][key] = self.methods[key].getAll()

        return ret

class Struct:
    def __init__(self, name):
        self.data = name
        self.fields = {}
        self.methods = {}
        self.name = name["name"]
        self.modifier = name["modifier"]

    def addField(self, key, data):
        self.fields[key] = Field(data)

    def addMethod(self, key, data):
        self.methods[key] = Method(data)

    def getMethods(self, key):
        ret = {}
        i = 0
        for key in self.methods:
            if key == name:
                ret[i] = cls[key]
            i += 1

    def getFields(self, key):
        ret = {}
        i = 0
        for key in self.fields:
            if key == name:
                ret[i] = cls[key]
            i += 1

    def getAll(self):
        ret = {}
        ret["fields"] = {}
        ret["name"] = self.name
        ret["modifier"] = self.modifier
        for key in self.fields:
            ret["fields"][key] = self.fields[key].getAll()

        ret["methods"] = {}
        for key in self.methods:
            ret["methods"][key] = self.methods[key].getAll()

        return ret

class Enum:
    def __init__(self, name):
        self.name = name
        self.fields = {}

    def addField(self, key, data):
        self.fields[key] = Field(data)

    def getAll(self):
        ret = {}
        ret["fields"] = {}
        ret["name"] = self.name
        for key in self.fields:
            ret["fields"][key] = self.fields[key].getAll()

        return ret

class Namespace:
    def __init__(self, name):
        self.name = name
        self.classes = {}
        self.structs = {}
        self.enums = {}

    def addClass(self, key, cl):
        self.classes[key] = Class(cl)

    def addStruct(self, key, cl):
        self.structs[key] = Struct(cl)

    def addEnum(self, key, cl):
        self.enums[key] = Enum(cl)

    def find(self, name):
        ret = {}
        i = 0
        for key in self.classes:
            if name in key:
                ret[i] = self.classes[key]
            i += 1

        for key in self.structs:
            if name in key:
                ret[i] = self.structs[key]
            i += 1

        for key in self.enums:
            if name in key:
                ret[i] = self.enums[key]
            i += 1
        return ret

    def get(self, type, key):
        if type == "class":
            return self.classes[key]
        elif type == "struct":
            return self.structs[key]
        else:
            return self.enums[key]

    def getAll(self):
        ret = {}

        ret["classes"] = {}
        for key in self.classes:
            ret["classes"][key] = self.classes[key].getAll()

        ret["enums"] = {}
        for key in self.enums:
            ret["enums"][key] = self.enums[key].getAll()

        ret["structs"] = {}
        for key in self.structs:
            ret["structs"][key] = self.structs[key].getAll()

        return ret

class Parser:
    def __init__(self, url):
        self.url = url
        self.namespaces = {}
        self.nearNamespaceName = "DefaultNamespace"  
        self.namespaces["DefaultNamespace"] = Namespace("DefaultNamespace") 
        self.near = None
        self.lastOffset = None
        self.nearClass = None
        self.nearEnum = None

    def getns(self, line):
        if "// Namespace: " in line:
            name = line.split("Namespace: ")[1].strip()
            if name == "":
                name = "NO_NAME_SPACE"
            if name not in self.namespaces:
                self.namespaces[name] = Namespace(name)
            self.nearNamespaceName = name

    def getClass(self, line):
        if " class " in line:
            name = ""
            types = {}
            try:
                if " : " in line:
                    name = line.split("class")[1].split(":")[0].strip()
                else:
                    name = line.split("class")[1].split("//")[0].strip()
                types = line.split(" class ")[0].split()
            except:
                return  
            if not self.nearNamespaceName in self.namespaces:
                self.nearNamespaceName = "DefaultNamespace"
                self.namespaces["DefaultNamespace"] = Namespace("DefaultNamespace")
            if name in self.namespaces[self.nearNamespaceName].classes:
                self.nearClass = name.strip() + "(1)"
            else:
                self.nearClass = name.strip()
            clasz = {}
            clasz["name"] = name.strip()
            clasz["modifier"] = types
            self.namespaces[self.nearNamespaceName].addClass(self.nearClass, clasz)
            self.near = "class"

    def getStruct(self, line):
        if " struct " in line:
            name = ""
            types = {}
            try:
                if " : " in line:
                    name = line.split("struct")[1].split(":")[0].strip()
                else:
                    name = line.split("struct")[1].split("//")[0].strip()
                types = line.split(" struct ")[0].split()
            except:
                return  
            if not self.nearNamespaceName in self.namespaces:
                self.nearNamespaceName = "DefaultNamespace"
                self.namespaces["DefaultNamespace"] = Namespace("DefaultNamespace")
            if name in self.namespaces[self.nearNamespaceName].structs:
                self.nearClass = name.strip() + "(1)"
            else:
                self.nearClass = name.strip()
            clasz = {}
            clasz["name"] = name.strip()
            clasz["modifier"] = types
            self.namespaces[self.nearNamespaceName].addStruct(self.nearClass, clasz)
            self.near = "struct"

    def getEnum(self, line):
        if "enum " in line:
            try:
                name = line.split("enum ")[1].split(" ")[0].strip()
            except:
                return  
            if not self.nearNamespaceName in self.namespaces:
                self.nearNamespaceName = "DefaultNamespace"
                self.namespaces["DefaultNamespace"] = Namespace("DefaultNamespace")
            enum = Enum(name)
            self.nearEnum = enum
            self.namespaces[self.nearNamespaceName].addEnum(name, enum)
            self.near = "enum"

    def getEnumField(self, line):
        if "public const" in line or "private const" in line:
            if self.near == "enum":
                try:
                    parts = line.strip().split(" ")
                    name = parts[-2]
                    value = parts[-1].rstrip(";")
                    field = {"name": name, "value": value}
                    self.nearEnum.addField(name, field)
                except:
                    pass  

    def getOffset(self, line):
        if "Offset: 0x" in line:
            try:
                offset = line.split("Offset: ")[1].split(" ")[0]
                self.lastOffset = offset
            except:
                pass  

    def getMethod(self, line):
        if ") { }" in line:
            try:
                name = line.split("(")[0].split()[-1]
                if ">" in line.split(f" {name}")[-2].split()[-1]:
                    type = line.split("<")[0].split()[-1] + "<" + line.split("<")[1].split(">")[0] + ">"
                else:
                    type = line.split(f" {name}")[0].split(" ")[-1]
                args = line.split("(")[1].split(")")[0]
                nameMeth = type + " " + name + "(" + args + ")"

                if not self.nearNamespaceName in self.namespaces:
                    self.nearNamespaceName = "DefaultNamespace"
                    self.namespaces["DefaultNamespace"] = Namespace("DefaultNamespace")

                data = {}
                data["name"] = name
                data["type"] = type
                data["offset"] = self.lastOffset
                data["modifier"] = line.split(f" {type}")[0].split()
                data["params"] = args.split(", ") if args else []

                self.namespaces[self.nearNamespaceName].get(self.near, self.nearClass).addMethod(name, data)
            except:
                pass  

    def getField(self, line):
        field_type = ["class", "struct"]
        if "; // 0x" in line and self.near in field_type:
            try:
                if "/*" in line:
                    line = line.split("/*")[0].strip() + line.split("*/")[1].strip()
                
                name = line.split("; // 0x")[0].split(" ")[-1]
                offset = "0x" + line.split("; // 0x")[1].split("\n")[0]
                if ">" in line.split(f" {name}")[-2].split()[-1]:
                    type = line.split("<")[0].split()[-1] + "<" + line.split("<")[1].split(">")[0] + ">"
                else:
                    type = line.split(f" {name}")[0].split(" ")[-1]
                
                modifiers = line.split(type)[0].strip().split()
                if not self.nearNamespaceName in self.namespaces:
                    self.nearNamespaceName = "DefaultNamespace"
                    self.namespaces["DefaultNamespace"] = Namespace("DefaultNamespace")
                
                data = {}
                data["name"] = name
                data["type"] = type
                data["offset"] = offset
                data["modifier"] = modifiers
                self.namespaces[self.nearNamespaceName].get(self.near, self.nearClass).addField(name, data)
            except:
                pass 

    def init(self):
        self.text = open(self.url, "r").readlines()

        for line in tqdm(self.text):
            line = line.strip()
            if not line:
                continue
            self.getns(line)
            self.getClass(line)
            self.getStruct(line)
            self.getEnum(line)
            self.getOffset(line)
            self.getMethod(line)
            self.getEnumField(line)
            self.getField(line)
        with open("out.json", "w") as outfile:
            json.dump(self.namespaces, outfile, indent=4, cls=CustomEncoder)