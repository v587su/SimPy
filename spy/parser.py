from tree_sitter import Parser, Language
import regex as re
import os
from .parser_utils import traverse_type, traverse_all_children, error_analyze
from .rules_py2spy import TRANSFORM_RULES as py2spy_rules, SPECIAL_TOKENS as spy_special_tokens, SPY_MAP_PY
from .rules_spy2py import TRANSFORM_RULES as spy2py_rules



class Transformer:
    def __init__(self, ignore_error=False):
        self.ignore_error = ignore_error
        self.py_parser = Parser()
        self.py_language = Language(os.path.join(os.path.dirname(__file__), 'build/python-languages.so'), 'python')
        self.py_parser.set_language(self.py_language)
        self.spy_parser = Parser()
        # self.spy_language = Language('spy/build/spython-languages.so', 'python')
        self.spy_language = Language(os.path.join(os.path.dirname(__file__), 'build/spython-languages.so'), 'python')
        self.spy_parser.set_language(self.spy_language)

        self.regex = {
            'comment': re.compile(r'#.*?(?=<[a-z_]+>)'),
            'string': re.compile(r'\'[^\']*\'|\"[^\"]*\"|\'\'\'[^\']*\'\'\'|\"\"\"[^\"]*\"\"\"'),
            'line_continue': re.compile(r'\\'),
            'comma': re.compile(r'<comma>'),
            'space': re.compile(r'<SPACE>'),
            'multi_spaces': re.compile(r'\s+'),
            'space_next_to_symbol': re.compile(r'(?<=[^a-zA-Z0-9_\*\s"]+)\s+|\s+(?=[^a-zA-Z0-9_\*\s"]+)'),
            'remove_line_sep': re.compile(r'(?<=<[a-z_]+_[a-z]+>)\s*<line_sep>|<line_sep>\s*(?=<[a-z_]+_(stmt|end|start|keyword)>)'),  # this is to merge multiple line_sep into one
            'tokens_without_line_sep': re.compile(r'(<[a-z_]+_[a-z]+>)+'),
            'spy_lines': re.compile(r'(<[a-z_]+>)+(.*?)(?=<[a-z_]+>)'),
        }

        self.transform = py2spy_rules
        self.spy2py_transform = spy2py_rules
        self.special_tokens = sorted(list(set(spy_special_tokens))) # ['<and>', '<arrow>', '<as>', '<assert_stmt>', '<async_keyword>', '<augadd>', '<augand>', '<augdiv>', '<augfloordiv>', '<auglshift>', '<augmatmul>', '<augmod>', '<augmul>', '<augor>', '<augpow>', '<augrshift>', '<augsub>', '<augxor>', '<await>', '<block_end>', '<block_start>', '<break>', '<case_stmt>', '<class_stmt>', '<concat>', '<continue>', '<def_stmt>', '<del_stmt>', '<elif_stmt>', '<ellipsis>', '<else>', '<else_stmt>', '<eq>', '<except_group_stmt>', '<except_stmt>', '<exec>', '<false>', '<finally_stmt>', '<floordiv>', '<for>', '<for_stmt>', '<from>', '<g>', '<ge>', '<global>', '<if>', '<if_stmt>', '<import_from_future_stmt>', '<import_from_stmt>', '<import_stmt>', '<in>', '<is>', '<isnot>', '<l>', '<lambda>', '<le>', '<lgne>', '<line_sep>', '<lshift>', '<match_stmt>', '<ne>', '<none>', '<nonlocal>', '<not>', '<notin>', '<or>', '<pass>', '<power>', '<print>', '<raise>', '<return>', '<rshift>', '<times>', '<true>', '<try_stmt>', '<while_stmt>', '<with_stmt>', '<yield>']
        self.special_tokens_py = [SPY_MAP_PY[token] for token in self.special_tokens]
        
        self.indent_spaces = 4
        self.masked = []

    def parse(self, code):
        nodes, edits = [], []
        tree = self.py_parser.parse(bytes(code, 'utf8'))
        traverse_all_children(tree.root_node, nodes)
        for node in nodes:
            if node.is_missing:
                raise ValueError('Python2 is not supported')
            if node.type in ['print', 'exec_statement', 'ERROR']:
                raise ValueError('Python2 is not supported')
            edit_func = self.transform.get(node.type, None)
            if edit_func:
                edits.extend(edit_func(node))
        bcode = self._py_edit(code, edits)
        code = bcode.decode('utf8')
        code = re.sub(self.regex['line_continue'], r' ', code)
        code = re.sub(self.regex['space_next_to_symbol'], r'', code)
        code = re.sub(self.regex['space'], r' ', code)
        code = re.sub(self.regex['multi_spaces'], r' ', code)
        code = re.sub(self.regex['remove_line_sep'], r'', code)
        parsed = ''
        prev_end = 0
        for i, (match, record) in enumerate(zip(re.finditer(r'["\']MASK["\']', code), self.masked)):
            if record.startswith('#'):
                record = record + '\n'
            if i == 0:
                parsed += code[:match.start()] + record
            else:
                parsed += code[prev_end:match.start()] + record
            prev_end = match.end()
        parsed += code[prev_end:]
        self.masked = []
        return parsed

    def decode(self, spy_code, debug=False):
        matches = list(self.regex['tokens_without_line_sep'].finditer(spy_code))
        if len(matches) == 0:
            py_code = spy_code
        else:
            py_code = ''
            prev_end = 0
            for i, match in enumerate(matches):
                if match.allcaptures()[1][0] in ['<line_sep>', '<block_start>', '<case_stmt>', '<elif_stmt>', '<else_stmt>', '<finally_stmt>', '<except_stmt>']:
                    py_code += spy_code[prev_end:match.end()]
                else:
                    py_code += spy_code[prev_end:match.start()] + \
                        '<line_sep>' + match.group(0)
                prev_end = match.end()
            py_code += spy_code[prev_end:]

        tree = self.spy_parser.parse(bytes(py_code, 'utf8'))
        errors = []
        traverse_type(tree.root_node, errors, 'ERROR')
        nodes, edits = [], []
        traverse_all_children(tree.root_node, nodes)
        for node in nodes:
            edit_func = self.spy2py_transform.get(node.type, None)
            if edit_func:
                edits.extend(edit_func(node))
        bcode = self._spy_edit(py_code, edits)
        py_code = bcode.decode('utf8')
        if debug:
            return py_code, (tree.root_node, errors)
        else:
            return py_code

    def _spy_edit(self, code, edits):
        bcode = bytes(code, 'utf8')
        edit_to_remove = []
        for edit in edits:
            if edit.action == 'cancel':
                for i, edit_to_check in enumerate(edits):
                    if edit == edit_to_check:
                        edit_to_remove.append(i)
        
        edits = [edit for i, edit in enumerate(edits) if i not in edit_to_remove]
    
        def sort_key(x):
            if x.action == 'append':
                return x.node.end_byte - x.priority
                # return x.node.start_byte - x.priority
            elif x.action == 'insert':
                return x.node.start_byte + 0.1 - x.priority
            elif x.action == 'replace':
                return x.node.start_byte + 0.3 - x.priority
            elif x.action == 'mask':
                return x.node.start_byte + 0.2 - x.priority
            elif x.action in ['indent']:
                return x.node.start_byte + 0.25 - x.priority
            elif x.action in ['dedent']:
                return x.node.start_byte + 0.06 - x.priority
            elif x.action == 'newline':
                return x.node.start_byte + 0.24 - x.priority
            else:
                return x.node.start_byte
        edits = sorted(edits, key=sort_key)
        margin = 0
        indent = 0
        for edit in edits:
            start_byte = edit.node.start_byte + margin
            end_byte = edit.node.end_byte + margin
            if edit.action == 'insert':
                content = bytes(edit.content,'utf8')
                bcode = bcode[:start_byte] + content + bcode[start_byte:]
                margin += len(content)
            elif edit.action == 'replace':
                content = bytes(edit.content,'utf8')
                bcode = bcode[:start_byte] + content + bcode[end_byte:]
                margin += len(content) - (end_byte - start_byte)
            elif edit.action == 'append':
                content = bytes(edit.content,'utf8')
                bcode = bcode[:end_byte] + content + bcode[end_byte:]
                margin += len(content)
            elif edit.action == 'mask':
                content = bytes(edit.content,'utf8')
                bcode = bcode[:start_byte] + content + bcode[end_byte:]
                margin += len(content) - (end_byte - start_byte)
                self.masked.append(edit.node.text.decode('utf8'))
            elif edit.action == 'indent':
                indent += self.indent_spaces
                bcode = bcode[:start_byte] + bytes('\n' + ' ' * indent,'utf8') + bcode[start_byte:]
                margin += indent + 1
            elif edit.action == 'dedent':
                indent -= self.indent_spaces
            elif edit.action == 'newline':
                bcode = bcode[:start_byte] + bytes('\n' + ' ' * indent,'utf8') + bcode[start_byte:]
                margin += indent + 1
                
            # print('***************'*2) 
            # print(start_byte, end_byte, edit, margin)
            # print('***************') 
            # print(str(bcode, 'utf8'))
            # print('***************'*2) 
        return bcode



    def _py_edit(self, code, edits):
        # remove conflicted edits
        bcode = bytes(code, 'utf8')
        edit_to_remove = []
        for edit in edits:
            if edit.action == 'cancel':
                for i, edit_to_check in enumerate(edits):
                    if edit == edit_to_check:
                        edit_to_remove.append(i)
        
        edits = [edit for i, edit in enumerate(edits) if i not in edit_to_remove]
    
        def sort_key(x):
            if x.action == 'append':
                return x.node.end_byte - x.priority
            elif x.action == 'insert':
                return x.node.start_byte + 0.1 - x.priority
            elif x.action == 'replace':
                return x.node.start_byte + 0.3 - x.priority
            elif x.action == 'mask':
                return x.node.start_byte + 0.2 - x.priority
            else:
                return x.node.start_byte
        edits = sorted(edits, key=sort_key)

        margin = 0
        for edit in edits:
            start_byte = edit.node.start_byte + margin
            end_byte = edit.node.end_byte + margin
            if edit.action == 'insert':
                bcode = bcode[:start_byte] + bytes(edit.content,'utf8') + bcode[start_byte:]
                margin += len(edit.content)
            elif edit.action == 'replace':
                bcode = bcode[:start_byte] + bytes(edit.content,'utf8') + bcode[end_byte:]
                margin += len(edit.content) - (end_byte - start_byte)
            elif edit.action == 'append':
                bcode = bcode[:end_byte] + bytes(edit.content,'utf8') + bcode[end_byte:]
                margin += len(edit.content)
            elif edit.action == 'mask':
                bcode = bcode[:start_byte] + bytes(edit.content,'utf8') + bcode[end_byte:]
                margin += len(edit.content) - (end_byte - start_byte)
                self.masked.append(edit.node.text.decode('utf8'))
            elif edit.action == 'dedent':
                indent = edit.node.start_point[1] + 1
                bcode = bcode[:start_byte - indent] + bcode[start_byte:]
                margin -= indent
            
            # print(edit)
            # print(str(bcode, 'utf8'))
        return bcode

