from dataclasses import dataclass

@dataclass
class Edit:
    node: object
    action: str = 'insert'
    content: str = ''
    priority: int = 0

    def __eq__(self, other):
        return self.node == other.node and self.content == other.content

@dataclass
class FakeNode:
    start_byte: int
    end_byte: int
    text: str

def traverse_all_children(node, results):
    results.append(node)
    if not node.children:
        return
    for n in node.children:
        traverse_all_children(n, results)

def traverse_type(node, results, kind):
    if node.type == kind:
        results.append(node)
    if not node.children:
        return
    for n in node.children:
        traverse_type(n, results, kind)


def error_analyze(origin_code, spy_code, py_code, errors):

    if len(errors) > 0:
        print(origin_code)
        # print(f'====================SPY_CODE====================')
        # print(spy_code)
        print(f'====================ENHANCED_SPY_CODE====================')
        print(py_code)
        print(f'===================={len(errors)} ERRORS====================')
        # for i,error in enumerate(errors):
            # print(f'---------Error {i}---------')
            # print(f'Start Point: {error.start_point}')
            # print(f'End Point: {error.end_point}')
            # print(f'Content: {error.text.decode("utf8")}')
            # if error.parent is not None:
                # print(f'Context: {error.parent.text.decode("utf8")}')
        raise Exception

def search_edits(nodes, action, target_type, content):
    edits = []
    for node in nodes:
        if node.type == target_type:
            edits.append(Edit(node=node, action=action, content=content))
    return edits

