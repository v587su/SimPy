from .parser_utils import search_edits, Edit, FakeNode

STMT_KEYWORDS = ['with', 'def', 'class',  'try', 'except', 'finally', 'match',  'while', 'assert', 'del', 'case','elif']

EXPR_KEYWORDS = ['and', 'or', 'not', 'is', 'return', 'raise', 'break', 'continue', 'pass', 'global', 'nonlocal', 'from', 'as', 'print', 'exec', 'in', 'true', 'false', 'none', ]

#'+=', '-=', '*=', '/=', '@=', '//=', '%=', '**=', '>>=', '<<=', '&=', '^=', '|=
OPER_KEYWORDS = {
    '//': '<floordiv>', '<': '<l>', '>': '<g>', '<<': '<lshift>', '>>': '<rshift>', '==': '<eq>', '!=': '<ne>', '<=': '<le>', '>=': '<ge>', '<>': '<lgne>', 'not in': '<notin>', 'is not': '<isnot>', '+=': '<augadd>', '-=': '<augsub>', '*=': '<augmul>', '/=': '<augdiv>', '@=': '<augmatmul>', '//=': '<augfloordiv>', '%=': '<augmod>', '**=': '<augpow>', '>>=': '<augrshift>', '<<=': '<auglshift>', '&=': '<augand>', '^=': '<augxor>', '|=': '<augor>', '->': '<arrow>', 'ellipsis': '<ellipsis>'
}

WILD_KEYWORDS = ['<augsub>', '<from>', '<ellipsis>', '<floordiv>', '<arrow>', '<yield>', '<ne>', '<else_stmt>', '<le>', '<lshift>', '<line_sep>', '<lgne>', '<except_group_stmt>', '<def_stmt>', '<g>', '<auglshift>', '<augmul>', '<l>', '<isnot>', '<augmatmul>', '<lambda>', '<augxor>', '<augdiv>', '<concat>', '<await>', '<augrshift>', '<ge>', '<power>', '<augadd>', '<import_stmt>', '<else>', '<eq>', '<augand>', '<if>', '<import_from_stmt>', '<augfloordiv>', '<finally_stmt>', '<augpow>', '<augor>', '<for>', '<augmod>', '<if_stmt>', '<in>', '<block_end>', '<times>', '<import_from_future_stmt>', '<notin>', '<block_start>', '<elif_stmt>', '<rshift>', '<except_stmt>', '<async_keyword>', '<case_stmt>', '<for_stmt>']

WILD_PY_KEYWORDS = ['-=', 'from', 'ellipsis', '//', '->', 'yield', '!=', 'else', '<=', '<<', '\n', '<>', 'except', 'def', '>', '<<=', '*=', '<', 'is not', '@=', 'lambda', '^=', '/=', '+', 'await', '>>=', '>=', '**', '+=', 'import', 'else', '==', '&=', 'if', 'from import', '//=', 'finally', '**=', '|=', 'for', '%=', 'if', 'in', '}', '*', 'from future import', 'not in', '{', 'elif', '>>', 'except', 'async', 'case', 'for']
# SPECIAL

def block_exp(node):
    if node.start_byte != node.end_byte:
        edits = [Edit(node=node, action='insert', content='<block_start>'), Edit(
        node=node, action='append', content='<block_end>')]
    else:
        return [Edit(node=node, action='insert', content='<block_start>', priority=0.5), Edit(
        node=node, action='append', content='<block_end>')]
    if len(node.children) == 0:
        return edits
    future_node_line = 0
    for i in range(len(node.children)):
        if node.children[-i-1].start_point[0] != future_node_line and node.children[-i-1].type not in ['comment', ';']:
            edits.append(Edit(node=node.children[-i-1], action='append', content='<line_sep>'))
        future_node_line = node.children[-i-1].start_point[0]
    return edits

def module(node):
    edits = []
    future_node_line = -1
    for i in range(len(node.children)):
        current_node = node.children[-i-1]
        if current_node.start_point[0] != future_node_line and current_node.type not in ['comment', ';']:
            edits.append(Edit(node=current_node, action='append', content='<line_sep>'))

        future_node_line = current_node.start_point[0]
    return edits

def comment_mask(node):
    return [Edit(node=node, action='mask', content="'MASK'")]

def string_mask(node):
    edits = []
    previous_node = None
    for c in node.children:
        if c.type == 'interpolation':
            if previous_node is not None:
                fake_node = FakeNode(start_byte=previous_node.end_byte, end_byte=c.start_byte, text=node.text[previous_node.end_byte - node.start_byte:c.start_byte - node.start_byte])
            else:
                fake_node = FakeNode(start_byte=node.start_byte, end_byte=c.start_byte, text=node.text[:c.start_byte - node.start_byte])
            edits.append(Edit(node=fake_node, action='mask', content='"MASK"'))
            previous_node = c
    if len(edits) == 0:
        edits.append(Edit(node=node, action='mask', content='"MASK"'))
    else:
        edits.append(Edit(node=FakeNode(start_byte=previous_node.end_byte, end_byte=node.end_byte, text=node.text[previous_node.end_byte - node.start_byte:]), action='mask', content='"MASK"'))
    return edits

def semicolon(node):
    return [Edit(node=node, action='replace', content='<line_sep>')]


def import_from_stmt(node):
    # from a import b
    edits = [Edit(node=node.children[0], action='replace', content='<import_from_stmt>'), Edit(node=node.children[0], action='cancel', content='<from>')]
    edits.extend(search_edits(node.children, 'replace', 'import', '<SPACE>'))
    edits.extend(search_edits(node.children, 'replace', ',', '<SPACE>'))
    edits.extend(search_edits(node.children, 'replace', '(', '<SPACE>'))
    edits.extend(search_edits(node.children, 'replace', ')', '<SPACE>'))
    return edits

def import_from_future_stmt(node):
    # from a import b

    edits = [Edit(node=node.children[0], action='replace', content='<import_from_future_stmt>'), Edit(node=node.children[0], action='cancel', content='<from>')]
    edits.extend(search_edits(node.children, 'replace', '__future__', ''))
    edits.extend(search_edits(node.children, 'replace', 'import', '<SPACE>'))
    edits.extend(search_edits(node.children, 'replace', ',', '<SPACE>'))
    edits.extend(search_edits(node.children, 'replace', '(', '<SPACE>'))
    edits.extend(search_edits(node.children, 'replace', ')', '<SPACE>'))
    return edits

def import_stmt(node):
    edits = [
        Edit(node=node.children[0], action='replace', content='<import_stmt>')
    ]
    edits.extend(search_edits(node.children, 'replace', ',', '<SPACE>'))
    edits.extend(search_edits(node.children, 'replace', '(', '<SPACE>'))
    edits.extend(search_edits(node.children, 'replace', ')', '<SPACE>'))
    return edits



# STATEMENTS

def def_stmt(node):
    # node to string
    # BEFORE: 'def' NAME '(' [params] ')' ['->' expression ] ':' [func_type_comment] block
    # AFTER: '<def_stmt>' NAME [params] ['->' expression ] [func_type_comment] block
    edits = []
    # params_node = node.child_by_field_name('parameters')
    # edits.append(
    #     Edit(node=params_node.children[0], action='replace', content='<SPACE>'))
    # edits.append(
    #     Edit(node=params_node.children[-1], action='replace', content=''))
    edits.extend(search_edits(node.children, 'replace', ':', ''))
    return edits

def class_stmt(node):
    edits = []
    edits.extend(search_edits(node.children, 'replace', ':', ''))
    return edits

def for_stmt(node):
    # BEFORE:  'for' star_targets 'in' star_expressions ':' block [else_block]
    # AFTER: '<for_stmt>' star_targets star_expressions block [else_block]
    edits = search_edits(node.children, 'replace', 'for', '<for_stmt>')
    edits.extend(search_edits(node.children, 'replace', 'in', '<SPACE>'))
    edits.extend(search_edits(node.children, 'cancel', 'in', '<in>'))
    edits.extend(search_edits(node.children, 'replace', ':', ''))
    return edits

def for_in_clause_stmt(node):
    edits = search_edits(node.children, 'replace', 'for', '<for>')
    edits.extend(search_edits(node.children, 'replace', 'in', '<SPACE>'))
    edits.extend(search_edits(node.children, 'cancel', 'in', '<in>'))
    edits.extend(search_edits(node.children, 'replace', ',', '<SPACE>'))
    return edits

def if_stmt(node):
    edits = [Edit(node=node.children[0],
                  action='replace', content='<if_stmt>')]
    edits.extend(search_edits(node.children, 'replace', ':', ''))
    return edits

def if_clause_stmt(node):
    edits = [Edit(node=node.children[0],
                  action='replace', content='<if>')]
    return edits

def else_clause_stmt(node):
    edits = [Edit(node=node.children[0],
                  action='replace', content='<else_stmt>'), Edit(node=node.children[0], action='cancel', content='<else>')]
    edits.extend(search_edits(node.children, 'replace', ':', ''))
    return edits

def match_stmt(node):
    edits = search_edits(node.children, 'replace', ':', '<block_start>')
    edits.extend(search_edits(node.children, 'replace', ',', '<SPACE>'))
    edits.append(
        Edit(node=node.children[-1], action='append', content='<block_end>'))
    return edits

def rest_compound_stmt(node):
    return search_edits(node.children, 'replace', ':', '')


def case_clause(node):
    edits = search_edits(node.children, 'replace', ':', '')
    edits.extend(search_edits(node.children, 'replace', ',', '<SPACE>'))
    edits.append(Edit(node=node, action='insert', content='<line_sep>'))
    return edits

def with_clause(node):
    edits = search_edits(node.children, 'replace', ',', '<SPACE>')
    edits.extend(search_edits(node.children, 'replace', '(', '<SPACE>'))
    edits.extend(search_edits(node.children, 'replace', ')', '<SPACE>'))
    return edits

def except_clause(node):
    edits = search_edits(node.children, 'replace', ':', '')
    edits.extend(search_edits(node.children, 'replace', ',', '<SPACE>'))
    edits.append(Edit(node=node, action='insert', content='<line_sep>'))
    return edits

def except_group_clause(node):
    # not sure if this is correct
    edits = [Edit(node=node.children[0], action='replace', content='<except_group_stmt>')]
    edits.extend(search_edits(node.children, 'replace', ':', ''))
    edits.append(Edit(node=node, action='insert', content='<line_sep>'))
    return edits


def clause_stmt(node):
    edits = search_edits(node.children, 'replace', ':', '')
    # if node.start_point[0] > node.parent.start_point[0]:
        # edits.append(Edit(node=node, action='dedent'))
    edits.append(Edit(node=node, action='insert', content='<line_sep>'))
    return edits

# EXPRESSIONS


def conditional_expr(node):
    edits = search_edits(node.children, 'replace', 'if', '<if>')
    edits.extend(search_edits(node.children, 'replace', 'else', '<else>'))
    return edits

def binary_operator(node):
    edits = search_edits(node.children, 'replace', '*', '<times>')
    edits.extend(search_edits(node.children, 'replace', '**', '<power>'))
    return edits

def concatenated_string(node):
    edits = [Edit(node=n, action='insert', content='<concat>') for n in node.children[1:] if n.type == 'string']
    return edits

def async_keyword(node):
    edits = [Edit(node=node, action='replace', content='<async_keyword>')]
    return edits

def lambda_stmt(node):
    if len(node.children)> 0:
        return []
    else:
        return [Edit(node=node, action='replace', content='<lambda>')]

def await_stmt(node):
    if len(node.children)> 0:
        return []
    else:
        return [Edit(node=node, action='replace', content='<await>')]

def yield_stmt(node):
    if len(node.children)> 0:
        return []
    else:
        return [Edit(node=node, action='replace', content='<yield>')]
    
def no_comma(node):
    return search_edits(node.children, 'replace', ',', '<SPACE>')

def parameters(node):
    edits = search_edits(node.children, 'replace', ',', '<SPACE>')
    edits.extend(search_edits(node.children, 'replace', '(', '<SPACE>'))
    edits.extend(search_edits(node.children, 'replace', ')', ''))
    return edits



TRANSFORM_RULES = {
    'function_definition': def_stmt,
    'class_definition': class_stmt,
    'for_statement': for_stmt,
    'string': string_mask,
    'comment': comment_mask,
    ';': semicolon,
    'with_statement': rest_compound_stmt,
    'try_statement': rest_compound_stmt,
    'if_statement': if_stmt,
    'if_clause': if_clause_stmt,
    'while_statement': rest_compound_stmt,
    'elif_clause': clause_stmt,
    'else_clause': else_clause_stmt,
    'except_clause': except_clause,
    'except_group_clause': except_group_clause,
    'finally_clause': clause_stmt,
    'case_clause': case_clause,
    'with_clause': with_clause,
    'expression_statement': no_comma,
    'assert_statement': no_comma,
    'subscript': no_comma,
    'class_pattern': no_comma,
    'global_statement': no_comma,
    'nonlocal_statement': no_comma,
    'block': block_exp,
    'async': async_keyword,
    'conditional_expression': conditional_expr,
    'binary_operator': binary_operator,
    'import_from_statement': import_from_stmt,
    'import_statement': import_stmt,
    'future_import_statement': import_from_future_stmt,
    'match_statement': match_stmt,
    'for_in_clause': for_in_clause_stmt,
    'module': module,
    'list': no_comma,
    'expression_list': no_comma,
    'tuple': no_comma,
    'set': no_comma,
    'dictionary': no_comma,
    'list_pattern': no_comma,
    'tuple_pattern': no_comma,
    'parameters': parameters, # changed from no_comma
    'lambda': lambda_stmt,
    'await': await_stmt,
    'yield': yield_stmt,
    'lambda_parameters': no_comma,
    'argument_list': no_comma,
    'concatenated_string': concatenated_string,
}

TRANSFORM_RULES.update({keyword: lambda node: [Edit(node=node, action='replace', content=f'<{node.type}_stmt>')] for keyword in STMT_KEYWORDS})
TRANSFORM_RULES.update({keyword: lambda node: [Edit(node=node, action='replace', content=f'<{node.type}>')] for keyword in EXPR_KEYWORDS})
TRANSFORM_RULES.update({k: lambda node, c=v: [Edit(node=node, action='replace', content=c)] for k,v in OPER_KEYWORDS.items()})


SPECIAL_TOKENS = WILD_KEYWORDS + [f'<{keyword}_stmt>' for keyword in STMT_KEYWORDS] + [f'<{keyword}>' for keyword in EXPR_KEYWORDS] + list(OPER_KEYWORDS.values())
WILD_MAP = {k:v for k,v in zip(WILD_KEYWORDS, WILD_PY_KEYWORDS)}

# SPY_MAP_PY = {f'<{keyword}_stmt>': keyword for keyword in STMT_KEYWORDS} + {f'<{keyword}>': keyword for keyword in EXPR_KEYWORDS} + {v: k for k,v in OPER_KEYWORDS.items()} + WILD_MAP
SPY_MAP_PY = {f'<{keyword}_stmt>': keyword for keyword in STMT_KEYWORDS}
SPY_MAP_PY.update({f'<{keyword}>': keyword for keyword in EXPR_KEYWORDS})
SPY_MAP_PY.update({v: k for k,v in OPER_KEYWORDS.items()})
SPY_MAP_PY.update(WILD_MAP)
