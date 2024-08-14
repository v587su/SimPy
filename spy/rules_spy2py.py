from .parser_utils import search_edits, Edit, FakeNode
from .rules_py2spy import STMT_KEYWORDS, EXPR_KEYWORDS, OPER_KEYWORDS


STMT_KEYWORDS = ['with', 'def', 'class', 'except', 'finally', 'match',  'while', 'assert', 'del', 'case','elif', 'else']

EXPR_KEYWORDS = ['and', 'or', 'not', 'is', 'from', 'as','in']

LINE_EXPR_KEYWORDS = ['return', 'raise', 'break', 'continue', 'pass', 'global', 'nonlocal',  'print', 'exec', 'lambda', 'yield', 'await']

#'+=', '-=', '*=', '/=', '@=', '//=', '%=', '**=', '>>=', '<<=', '&=', '^=', '|=
OPER_KEYWORDS = {
    '//': '<floordiv>', '<': '<l>', '>': '<g>', '<<': '<lshift>', '>>': '<rshift>', '==': '<eq>', '!=': '<ne>', '<=': '<le>', '>=': '<ge>', '<>': '<lgne>',  '+=': '<augadd>', '-=': '<augsub>', '*=': '<augmul>', '/=': '<augdiv>', '@=': '<augmatmul>', '//=': '<augfloordiv>', '%=': '<augmod>', '**=': '<augpow>', '>>=': '<augrshift>', '<<=': '<auglshift>', '&=': '<augand>', '^=': '<augxor>', '|=': '<augor>', '->': '<arrow>', 'Ellipsis': 'ellipsis', 'async ': '<async_keyword>', '*':'<times>', '**': '<power>'
}


def scope_indent(node):
    return [Edit(node=node, action='indent'), Edit(node=node, action='replace', content='')]

def scope_dedent(node):
    return [Edit(node=node, action='dedent'), Edit(node=node, action='replace', content=''), Edit(node=FakeNode(start_byte=node.end_byte, end_byte=node.end_byte, text=node.text), action='newline')]

def line_sep(node):
    return [Edit(node=node, action='newline'), Edit(node=node, action='replace', content='')]


def comment(node):
    return [Edit(node=FakeNode(start_byte=node.end_byte+1, end_byte=node.end_byte, text=node.text), action='newline')]


def import_from_stmt(node):
    # <import_from_stmt> a b 
    edits = [Edit(node=node.children[0], action='replace', content='from '), Edit(node=node.children[1], action='append', content=' import')]
    edits.extend(search_edits(node.children, 'replace', ' ', ', ')[1:])
    return edits

def import_from_future_stmt(node):
    edits = [Edit(node=node.children[0], action='replace', content='from __future__ import')]
    edits.extend(search_edits(node.children, 'replace', ' ', ', '))
    return edits

def import_stmt(node):
    edits = [Edit(node=node.children[0], action='replace', content='import ')]
    edits.extend(search_edits(node.children, 'replace', ' ', ', '))
    return edits



# STATEMENTS

def def_stmt(node):
    non_comment_children = [n for n in node.children if n.type != 'comment']
    edits = [Edit(node=non_comment_children[-2], action='append', content=':', priority=0.6)]
    
    params = node.child_by_field_name('parameters')
    if not params:
        name = node.child_by_field_name('name')
        edits.append(Edit(node=name, action='append', content='()', priority=0.7))
    return edits

def parameters(node):
    edits = [Edit(node=node, action='insert', content='('), Edit(node=node, action='append', content=')', priority=0.7)]
    edits.extend(search_edits(node.children, 'replace', ' ', ', '))
    return edits


def class_stmt(node):
    non_comment_children = [n for n in node.children if n.type != 'comment']
    edits = [Edit(node=non_comment_children[-2], action='append', content=':', priority=0.6)]
    # body = node.child_by_field_name('body')
    # edits = [Edit(node=body, action='insert', content=':')]
    return edits

def for_stmt(node):

    non_comment_children = [n for n in node.children if n.type != 'comment']
    edits = [Edit(node=non_comment_children[-2], action='append', content=':', priority=0.6)]
    edits.extend(search_edits(node.children, 'replace', '<for_stmt>', 'for '))
    edits.extend(search_edits(node.children, 'replace', ' ', ' in '))

    # body = node.child_by_field_name('body')
    # edits.append(Edit(node=body, action='insert', content=':'))
    return edits

def for_in_clause_stmt(node):
    edits = search_edits(node.children, 'replace', '<for>', ' for ')
    count = 0
    for c in node.children:
        if c.type == ' ':
            if count == 0:
                edits.append(Edit(node=c, action='replace', content=' in '))
            else:
                edits.append(Edit(node=c, action='replace', content=', '))
    return edits

def if_stmt(node):
    edits = search_edits(node.children, 'replace', '<if_stmt>', 'if ')
    previous_node = None
    for node in node.children:
        if node.type != 'comment':
            if node.type == 'block':
                edits.append(Edit(node=previous_node, action='append', content=':', priority=0.6))
                break
            previous_node = node
 
    return edits

def if_clause_stmt(node):
    edits = search_edits(node.children, 'replace', '<if>', ' if ')
    return edits

# def if_else_clause_stmt(node):
    # edits = search_edits(node.children, 'replace', '<else>', ' else ')
    

def newline_clause_stmt(node):
    # non_comment_children = [n for n in node.children if n.type != 'comment']
    edits = [Edit(node=node, action='newline')]
    # edits = [Edit(node=node, action='newline'),Edit(node=non_comment_children[-2], action='append', content=':', priority=0.6)]
    
    previous_node = None
    for node in node.children:
        if node.type != 'comment':
            if node.type == 'block':
                edits.append(Edit(node=previous_node, action='append', content=':', priority=0.6))
                break
            previous_node = node
    return edits

def match_stmt(node):
    edits = no_comma(node)
    edits.extend(rest_compound_stmt(node))
    return edits

def try_stmt(node):
    edits = search_edits(node.children, 'replace', '<try_stmt>', 'try:')
    return edits

def rest_compound_stmt(node):
    edits = []
    previous_node = None
    for node in node.children:
        if node.type != 'comment':
            if node.type == 'block':
                edits.append(Edit(node=previous_node, action='append', content=':', priority=0.6))
                break
            previous_node = node
    return edits


def case_clause(node):
    edits = search_edits(node.children, 'replace', ':', '')
    edits.extend(search_edits(node.children, 'replace', ',', '<SPACE>'))
    edits.append(Edit(node=node, action='insert', content='<line_sep>'))
    return edits

# def with_clause(node):
#     edits = search_edits(node.children, 'replace', ',', '<SPACE>')
#     edits.extend(search_edits(node.children, 'replace', '(', '<SPACE>'))
#     edits.extend(search_edits(node.children, 'replace', ')', '<SPACE>'))
#     return edits

def except_clause(node):
    edits = [Edit(node=node, action='newline')]
    # edits.extend(search_edits(node.children, 'replace', '<except_stmt>', 'except '))
    previous_node = None
    for node in node.children:
        if node.type != 'comment':
            if node.type == 'block':
                edits.append(Edit(node=previous_node, action='append', content=':', priority=0.6))
                break
            previous_node = node
    return edits

def except_group_clause(node):
    # not sure if this is correct
    edits = [Edit(node=node.children[0], action='replace', content='<except_group_stmt>')]
    edits.extend(search_edits(node.children, 'replace', ':', ''))
    edits.append(Edit(node=node, action='insert', content='<line_sep>'))
    return edits


def clause_stmt(node):

    non_comment_children = [n for n in node.children if n.type != 'comment']
    edits = [Edit(node=non_comment_children[-2], action='append', content=':', priority=0.6)]
    # edits = search_edits(node.children, 'replace', ':', '')
    # if node.start_point[0] > node.parent.start_point[0]:
        # edits.append(Edit(node=node, action='dedent'))
    # edits.append(Edit(node=node, action='insert', content='<line_sep>'))
    return edits

# EXPRESSIONS
def notin_expr(node):
    return [Edit(node, action='replace', content=node.text.decode('utf-8').replace('<', ' ').replace('>', ' '))]


def conditional_expr(node):
    edits = search_edits(node.children, 'replace', '<if>', ' if ')
    edits.extend(search_edits(node.children, 'replace', '<else>', ' else '))
    return edits


def concatenated_string(node):
    edits = search_edits(node.children, 'replace', '<concat>', ' ')
    return edits

def no_comma(node):
    return search_edits(node.children, 'replace', ' ', ', ')



TRANSFORM_RULES = {
    '<line_sep>': line_sep,
    '<block_start>': scope_indent,
    '<block_end>': scope_dedent,
    'comment': comment,
    'function_definition': def_stmt,
    'class_definition': class_stmt,
    'for_statement': for_stmt,
    'with_statement': rest_compound_stmt,
    'try_statement': try_stmt,
    'if_statement': if_stmt,
    'if_clause': if_clause_stmt,

    'while_statement': rest_compound_stmt,
    'elif_clause': newline_clause_stmt,
    'else_clause': newline_clause_stmt,
    'except_clause': except_clause,
    'conditional_expression': conditional_expr,
    '<notin>': notin_expr,
    '<isnot>': notin_expr,
    # 'except_group_clause': except_group_clause,
    'finally_clause': clause_stmt,
    'case_clause': newline_clause_stmt,
    'with_clause': no_comma,
    'expression_statement': no_comma,
    'assert_statement': no_comma,
    'subscript': no_comma,
    'class_pattern': no_comma,
    'global_statement': no_comma,
    'nonlocal_statement': no_comma,
    'import_from_statement': import_from_stmt,
    'import_statement': import_stmt,
    'future_import_statement': import_from_future_stmt,
    'match_statement': match_stmt,
    'for_in_clause': for_in_clause_stmt,
    'list': no_comma,
    'expression_list': no_comma,
    'tuple': no_comma,
    'set': no_comma,
    'dictionary': no_comma,
    'list_pattern': no_comma,
    'tuple_pattern': no_comma,
    'parameters': parameters,
    'lambda_parameters': no_comma,
    'type_parameter': no_comma,
    'argument_list': no_comma,
    'concatenated_string': concatenated_string,

    'none': lambda node: [Edit(node=node, action='replace', content=' None ')],
    'true': lambda node: [Edit(node=node, action='replace', content=' True ')],
    'false': lambda node: [Edit(node=node, action='replace', content=' False ')],
}

TRANSFORM_RULES.update({f'<{keyword}_stmt>': lambda node, c=keyword: [Edit(node=node, action='replace', content=f'{c} ')] for keyword in STMT_KEYWORDS})
TRANSFORM_RULES.update({f'<{keyword}>': lambda node, c=keyword: [Edit(node=node, action='replace', content=f' {c} ')] for keyword in EXPR_KEYWORDS})
TRANSFORM_RULES.update({f'<{keyword}>': lambda node, c=keyword: [Edit(node=node, action='replace', content=f'{c} ')] for keyword in LINE_EXPR_KEYWORDS})
TRANSFORM_RULES.update({v: lambda node, c=k: [Edit(node=node, action='replace', content=c)] for k,v in OPER_KEYWORDS.items()})

