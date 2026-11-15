import ast
import re

with open("app.py", "r", encoding="utf-8") as f:
    tree = ast.parse(f.read(), filename="app.py")

routes = []
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call) and getattr(dec.func, 'attr', None) == 'route':
                route_path = dec.args[0].value if dec.args and isinstance(dec.args[0], ast.Constant) else "?"
                methods = []
                for kw in dec.keywords:
                    if kw.arg == 'methods' and isinstance(kw.value, ast.List):
                        methods = [elt.value for elt in kw.value.elts if isinstance(elt, ast.Constant)]
                routes.append((route_path, methods or ['GET'], node.name))

for path, methods, func in routes:
    print(f"{path:<35} {str(methods):<20} {func}")
