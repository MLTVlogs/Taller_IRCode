# grammar.py (versión actualizada para nuevo AST)
import logging
import sly
from rich import print
from dataclasses import dataclass
from typing import List, Any, Optional, Union
from lexer  import Lexer
from errors import error, errors_detected
from model  import *
from graphviz import *


def _L(node, lineno):
	node.lineno = lineno
	return node

# CLASES DE NODOS
# ---------- Types ----------
class Type:
	...

@dataclass(frozen=True)
class SimpleType(Type):
	name: str

@dataclass(frozen=True)
class ArrayType(Type):
	elem: Type

@dataclass(frozen=True)
class ArraySizedType(Type):
	size_expr: "Expr"
	elem: Type

@dataclass(frozen=True)
class FuncType(Type):
	ret: Type
	params: List["Param"]

@dataclass(frozen=True)
class Param:
	name: str
	typ: Type

# ---------- Program / Decl ----------
class Decl:
	...

@dataclass
class Program:
	decls: List[Decl]

@dataclass
class DeclTyped(Decl):
	name: str
	typ: Type

@dataclass
class DeclInit(Decl):
	name: str
	typ: Type
	init: Any

# ---------- Statement ----------
class Stmt:
	...

@dataclass
class Print(Stmt):
	values: List["Expr"]

@dataclass
class Return(Stmt):
	value: Optional["Expr"]

@dataclass
class Break(Stmt):
	...

@dataclass
class Continue(Stmt):
	...

@dataclass
class Block(Stmt):
	stmts: List[Union[Stmt, Decl]]

@dataclass
class ExprStmt(Stmt):
	expr: "Expr"

@dataclass
class If(Stmt):
	cond: Optional["Expr"]
	then: Stmt
	otherwise: Optional[Stmt] = None

@dataclass
class For(Stmt):
	init: Optional["Expr"]
	cond: Optional["Expr"]
	step: Optional["Expr"]
	body: Stmt

@dataclass
class While(Stmt):
	cond: Optional["Expr"]
	body: Stmt

# ---------- Expressions ----------
class Expr:
	...

@dataclass
class Name(Expr):
	id: str

@dataclass
class Literal(Expr):
	kind: str
	value: Any

@dataclass
class Index(Expr):
	base: Expr
	indices: List[Expr]

@dataclass
class Call(Expr):
	func: str
	args: List[Expr]

@dataclass
class Assign(Expr):
	target:Expr
	value: Expr

@dataclass
class BinOp(Expr):
	op: str
	left: Expr
	right: Expr

@dataclass
class UnaryOp(Expr):
	op: str
	expr: Expr

@dataclass
class PrefixOp(Expr):
	op: str
	expr: Expr

@dataclass
class PostfixOp(Expr):
	op: str
	expr: Expr

# PARSER
class Parser(sly.Parser):
	log = logging.getLogger()
	log.setLevel(logging.ERROR)
	expected_shift_reduce = 1
	debugfile='grammar.txt'
	
	tokens = Lexer.tokens
	
	# =================================================
	# PROGRAMA
	# =================================================
	
	@_("decl_list")
	def prog(self, p):
		return _L(Program(p[0]), p.lineno)
	
	# =================================================
	# LISTAS DE DECLARACIONES
	# =================================================
	
	@_("decl decl_list")
	def decl_list(self, p):
		return [p[0]] + p[1]
		
	@_("empty")
	def decl_list(self, p):
		return []
		
	# =================================================
	# DECLARACIONES
	# =================================================
	
	@_("ID ':' type_simple ';'")
	def decl(self, p):
		return _L(DeclTyped(p[0],p[2]), p.lineno)
		
	@_("ID ':' type_array_sized ';'")
	def decl(self, p):
		return _L(DeclTyped(p[0],p[2]), p.lineno)
		
	@_("ID ':' type_func ';'")
	def decl(self, p):
		return _L(DeclTyped(p[0],p[2]), p.lineno)
		
	@_("decl_init")
	def decl(self, p):
		return p[0]
		
	# === DECLARACIONES con inicialización
	
	@_("ID ':' type_simple '=' expr ';'")
	def decl_init(self, p):
		return _L(DeclInit(p[0],p[2],p[4]), p.lineno)
		
	@_("ID ':' CONSTANT '=' expr ';'")
	def decl_init(self, p):
		return _L(DeclInit(p[0],SimpleType("const"),p[4]), p.lineno)
		
	@_("ID ':' type_array_sized '=' '{' opt_expr_list '}' ';'")
	def decl_init(self, p):
		return _L(DeclInit(p[0],p[2],p[5]), p.lineno)
		
	@_("ID ':' type_func '=' '{' opt_stmt_list '}'")
	def decl_init(self, p):
		return _L(DeclInit(p[0],p[2],p[5]), p.lineno)
		
	# =================================================
	# STATEMENTS
	# =================================================
	
	@_("stmt_list")
	def opt_stmt_list(self, p):
		return p[0]
		
	@_("empty")
	def opt_stmt_list(self, p):
		return []
		
	@_("stmt stmt_list")
	def stmt_list(self, p):
		return [p[0]] + p[1]
		
	@_("stmt")
	def stmt_list(self, p):
		return [p[0]]
		
	@_("open_stmt")
	@_("closed_stmt")
	def stmt(self, p):
		return p[0]

	@_("if_stmt_closed")
	@_("for_stmt_closed")
	@_("while_stmt_closed")
	@_("simple_stmt")
	def closed_stmt(self, p):
		return p[0]

	@_("if_stmt_open")
	@_("for_stmt_open")
	@_("while_stmt_open")
	def open_stmt(self, p):
		return p[0]

	# -------------------------------------------------
	# IF
	# -------------------------------------------------
	
	@_("IF '(' opt_expr ')'")
	def if_cond(self, p):
		return p[2]
		
	@_("if_cond closed_stmt ELSE closed_stmt")
	def if_stmt_closed(self, p):
		return _L(If(p[0],p[1],p[3]), p.lineno)
		
	@_("if_cond stmt")
	def if_stmt_open(self, p):
		return _L(If(p[0],p[1]), p.lineno)
		
	@_("if_cond closed_stmt ELSE if_stmt_open")
	def if_stmt_open(self, p):
		return _L(If(p[0],p[1],p[3]), p.lineno)
		
	# -------------------------------------------------
	# FOR
	# -------------------------------------------------
	
	@_("FOR '(' opt_expr ';' opt_expr ';' opt_expr ')'")
	def for_header(self, p):
		return (p[2], p[4], p[6])
		
	@_("for_header open_stmt")
	def for_stmt_open(self, p):
		return _L(For(p[0][0],p[0][1],p[0][2],p[2]), p.lineno)
		
	@_("for_header closed_stmt")
	def for_stmt_closed(self, p):
		return _L(For(p[0][0],p[0][1],p[0][2],p[1]), p.lineno)
		
	# -------------------------------------------------
	# WHILE
	# -------------------------------------------------
	
	@_("WHILE '(' opt_expr ')'")
	def while_cond(self, p):
		return p[2]

	@_("while_cond open_stmt")
	def while_stmt_open(self, p):
		return _L(While(p[0],p[1]), p.lineno)
		
	@_("while_cond closed_stmt")
	def while_stmt_closed(self, p):
		return _L(While(p[0],p[1]), p.lineno)
		
	# -------------------------------------------------
	# SIMPLE STATEMENTS
	# -------------------------------------------------
	
	@_("print_stmt")
	@_("return_stmt")
	@_("break_stmt")
	@_("continue_stmt")
	@_("block_stmt")
	@_("decl")
	@_("expr ';'")
	def simple_stmt(self, p):
		return p[0]

	# PRINT
	@_("PRINT opt_expr_list ';'")
	def print_stmt(self, p):
		return _L(Print(p[1]), p)
		
	# RETURN
	@_("RETURN opt_expr ';'")
	def return_stmt(self, p):
		return _L(Return(p[1]), p.lineno)

	@_("BREAK ';'")
	def break_stmt(self, p):
		return _L(Break(), p.lineno)

	@_("CONTINUE ';'")
	def continue_stmt(self, p):
		return _L(Continue(), p.lineno)

	# BLOCK
	@_("'{' stmt_list '}'")
	def block_stmt(self, p):
		return _L(Block(p[1]), p.lineno)
		
	# =================================================
	# EXPRESIONES
	# =================================================
	
	@_("empty")
	def opt_expr_list(self, p):
		return []
		
	@_("expr_list")
	def opt_expr_list(self, p):
		return p[0]
		
	@_("expr ',' expr_list")
	def expr_list(self, p):
		return [p[0]] + p[2]
		
	@_("expr")
	def expr_list(self, p):
		return [p[0]]
		
	@_("empty")
	def opt_expr(self, p):
		return None
		
	@_("expr")
	def opt_expr(self, p):
		return p[0]
		
	# -------------------------------------------------
	# PRIMARY
	# -------------------------------------------------
	
	@_("expr1")
	def expr(self, p):
		return p[0]
		
	@_("lval  '='  expr1")
	@_("lval ADDEQ expr1")
	@_("lval SUBEQ expr1")
	@_("lval MULEQ expr1")
	@_("lval DIVEQ expr1")
	@_("lval MODEQ expr1")
	def expr1(self, p):
		return _L(Assign(p[0],p[2]), p.lineno)
		
	@_("expr2")
	def expr1(self, p):
		return p[0]
		
	# ----------- LVALUES -------------------
	
	@_("ID")
	def lval(self, p):
		return _L(Name(p[0]),p.lineno)
		
	@_("ID index")
	def lval(self, p):
		return p[0] + p[1]
		
	# -------------------------------------------------
	# OPERADORES
	# -------------------------------------------------
	
	@_("expr2 LOR expr3")
	def expr2(self, p):
		return _L(BinOp(p[1],p[0],p[2]),p.lineno)
		
	@_("expr3")
	def expr2(self, p):
		return p[0]
		
	@_("expr3 LAND expr4")
	def expr3(self, p):
		return _L(BinOp(p[1],p[0],p[2]),p.lineno)
		
	@_("expr4")
	def expr3(self, p):
		return p[0]
		
	@_("expr4 EQ expr5")
	@_("expr4 NE expr5")
	@_("expr4 LT expr5")
	@_("expr4 LE expr5")
	@_("expr4 GT expr5")
	@_("expr4 GE expr5")
	def expr4(self, p):
		return _L(BinOp(p[1],p[0],p[2]),p.lineno)

	@_("expr5")
	def expr4(self, p):
		return p[0]
		
	@_("expr5 '+' expr6")
	@_("expr5 '-' expr6")
	def expr5(self, p):
		return _L(BinOp(p[1],p[0],p[2]),p.lineno)
		
	@_("expr6")
	def expr5(self, p):
		return p[0]
		
	@_("expr6 '*' expr7")
	@_("expr6 '/' expr7")
	@_("expr6 '%' expr7")
	def expr6(self, p):
		return _L(BinOp(p[1],p[0],p[2]),p.lineno)
		
	@_("expr7")
	def expr6(self, p):
		return p[0]
		
	@_("expr7 '^' expr8")
	def expr7(self, p):
		return _L(BinOp(p[1],p[0],p[2]),p.lineno)
		
	@_("expr8")
	def expr7(self, p):
		return p[0]
		
	@_("'-' expr8")
	@_("'!' expr8")
	def expr8(self, p):
		return _L(UnaryOp(p[0],p[1]),p.lineno)

	@_("expr9")
	def expr8(self, p):
		return p[0]

	@_("postfix")
	def expr9(self, p):
		return p[0]

	@_("primary")
	def postfix(self, p):
		return p[0]

	@_("postfix INC")
	def postfix(self, p):
		return _L(PostfixOp(p[0],p[1]),p.lineno)

	@_("postfix DEC")
	def postfix(self, p):
		return _L(PostfixOp(p[0],p[1]),p.lineno)

	@_("prefix")
	def primary(self, p):
		return p[0]

	@_("INC prefix")
	def prefix(self, p):
		return _L(PrefixOp(p[0],p[1]),p.lineno)

	@_("DEC prefix")
	def prefix(self, p):
		return _L(PrefixOp(p[0],p[1]),p.lineno)

	@_("group")
	def prefix(self, p):
		return p[0]
		
	@_("'(' expr ')'")
	def group(self, p):
		return (p[1])

	@_("ID '(' opt_expr_list ')'")
	def group(self, p):
		return _L(Call(p[0],p[2]), p.lineno)
		
	@_("ID index")
	def group(self, p):
		return p[0], p[1]
		
	@_("factor")
	def group(self, p):
		return p[0]
		
	# INDICE DE ARREGLO
	@_("'[' expr ']'")
	def index(self, p):
		return [p[1]]
	
	# -------------------------------------------------
	# FACTORES
	# -------------------------------------------------
	
	@_("ID")
	def factor(self, p):
		return p[0]
		
	@_("INTEGER_LITERAL")
	def factor(self, p):
		return _L(Literal("int", p[0]), p.lineno)
		
	@_("FLOAT_LITERAL")
	def factor(self, p):
		return _L(Literal("float", p[0]), p.lineno)
		
	@_("CHAR_LITERAL")
	def factor(self, p):
		return _L(Literal("char", p[0]), p.lineno)
		
	@_("STRING_LITERAL")
	def factor(self, p):
		return _L(Literal("string", p[0]), p.lineno)
		
	@_("TRUE", "FALSE")
	def factor(self, p):
		return _L(Literal("bool", p[0]), p.lineno)
		
	# =================================================
	# TIPOS
	# =================================================
	
	@_("INTEGER")
	@_("FLOAT")
	@_("BOOLEAN")
	@_("CHAR")
	@_("STRING")
	@_("VOID")
	def type_simple(self, p):
		return SimpleType(p[0])
		
	@_("ARRAY '[' ']' type_simple")
	@_("ARRAY '[' ']' type_array")
	def type_array(self, p):
		return ArrayType(p[3])
		
	@_("ARRAY index type_simple")
	@_("ARRAY index type_array_sized")
	def type_array_sized(self, p):
		return ArraySizedType(p[1], p[2])
		
	@_("FUNCTION type_simple '(' opt_param_list ')'")
	@_("FUNCTION type_array_sized '(' opt_param_list ')'")
	def type_func(self, p):
		return FuncType(p[1], p[3])
		
	@_("empty")
	def opt_param_list(self, p):
		return []
		
	@_("param_list")
	def opt_param_list(self, p):
		return p[0]
		
	@_("param_list ',' param")
	def param_list(self, p):
		return p[0] + [p[2]]
		
	@_("param")
	def param_list(self, p):
		return [p[0]]
		
	@_("ID ':' type_simple")
	def param(self, p):
		return Param(p[0], p[2])
		
	@_("ID ':' type_array")
	def param(self, p):
		return Param(p[0], p[2])
		
	@_("ID ':' type_array_sized")
	def param(self, p):
		return Param(p[0], p[2])
		
	# =================================================
	# UTILIDAD: EMPTY
	# =================================================
	
	@_("")
	def empty(self, p):
		pass
		
	def error(self, p):
		lineno = p.lineno if p else 'EOF'
		value = repr(p.value) if p else 'EOF'
		error(f'Syntax error at {value}', lineno)
		
# ===================================================
# Utilidad: convertir algo en bloque si no lo es
# ===================================================
def as_block(x):
	if isinstance(x, Block):
		return x
	if isinstance(x, list):
		return Block(x)
	return Block([x])
	
	
# Convertir AST a diccionario
def ast_to_dict(node):
	if isinstance(node, list):
		return [ast_to_dict(item) for item in node]
	elif hasattr(node, "__dict__"):
		return {key: ast_to_dict(value) for key, value in node.__dict__.items()}
	else:
		return node

# ===================================================
# test
# ===================================================
def parse(txt):
	l = Lexer()
	p = Parser()	
	return p.parse(l.tokenize(txt))
	
	
if __name__ == '__main__':
	import sys, json
	
	if sys.platform != 'ios':
	
		if len(sys.argv) != 2:
			raise SystemExit("Usage: python gparse.py <filename>")
			
		filename = sys.argv[1]
		
	else:
		from file_picker import file_picker_dialog
		
		filename = file_picker_dialog(
			title='Seleccionar una archivo',
			root_dir='./test/',
			file_pattern='^.*[.]bpp'
		)
		
	if filename:
		txt = open(filename, encoding='utf-8').read()
		ast = parse(txt)
		if not errors_detected():
			print(ast)

		
		
